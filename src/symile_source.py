"""
Leitura do Symile-MIMIC bruto (credenciado).

Este modulo isola tudo o que depende do formato original do dataset. O restante
da aplicacao consome o subconjunto ja organizado por paciente (ver `loaders`).

Contexto importante do material que recebemos: apenas parte do dataset foi
disponibilizada. As tabelas estao completas, mas os tensores de imagem e sinal
nao: `cxr_test.npy` chegou truncado e os `ecg_*.npy` nao vieram. Ver
`docs/01-estudo-dataset-symile-mimic.md`.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def caminho_cxr_test(fonte: Path | None = None) -> Path:
    fonte = fonte or config.diretorio_fonte()
    return fonte / "data_npy" / "test" / "cxr_test.npy"


def _ler_cabecalho_npy(arquivo) -> tuple[tuple[int, ...], np.dtype, int]:
    """Le o cabecalho de um .npy e devolve (shape, dtype, offset dos dados)."""
    versao = np.lib.format.read_magic(arquivo)
    if versao == (1, 0):
        shape, _, dtype = np.lib.format.read_array_header_1_0(arquivo)
    elif versao == (2, 0):
        shape, _, dtype = np.lib.format.read_array_header_2_0(arquivo)
    else:
        raise ValueError(f"Versao de .npy nao suportada: {versao}")
    return shape, dtype, arquivo.tell()


def cxrs_recuperaveis(fonte: Path | None = None) -> tuple[np.ndarray, int]:
    """
    Le as radiografias intactas do `cxr_test.npy`, que chegou truncado.

    `np.load` falha neste arquivo porque o cabecalho declara mais imagens do que
    o arquivo contem. Lemos o cabecalho manualmente e carregamos apenas as
    imagens completas.

    Returns:
        (imagens, n_declarado): tensor (n, 3, 320, 320) com as imagens
        efetivamente presentes e o total que o cabecalho declara.
    """
    caminho = caminho_cxr_test(fonte)
    with open(caminho, "rb") as arquivo:
        shape, dtype, offset = _ler_cabecalho_npy(arquivo)
        valores_por_imagem = int(np.prod(shape[1:]))
        bytes_por_imagem = valores_por_imagem * dtype.itemsize
        bytes_disponiveis = caminho.stat().st_size - offset
        n_completas = bytes_disponiveis // bytes_por_imagem
        imagens = np.fromfile(
            arquivo, dtype=dtype, count=int(n_completas) * valores_por_imagem
        )
    return imagens.reshape((int(n_completas), *shape[1:])), int(shape[0])


def cxr_para_uint8(imagem: np.ndarray) -> np.ndarray:
    """
    Desfaz a normalizacao ImageNet de uma radiografia (3, 320, 320) e devolve
    uma imagem (320, 320, 3) em uint8, pronta para salvar como PNG.
    """
    media = np.array(config.IMAGENET_MEAN, dtype=np.float32).reshape(3, 1, 1)
    desvio = np.array(config.IMAGENET_STD, dtype=np.float32).reshape(3, 1, 1)
    desnormalizada = imagem * desvio + media
    return (np.clip(desnormalizada, 0.0, 1.0) * 255).astype(np.uint8).transpose(1, 2, 0)


def casos_positivos_do_test(fonte: Path | None = None) -> pd.DataFrame:
    """
    Casos do split de teste que servem de base para o subconjunto.

    O `test.csv` esta no formato da tarefa de retrieval: as primeiras 464 linhas
    sao os positivos (uma por admissao, todas distintas) e as demais sao
    candidatos negativos. A ordem das linhas dos positivos corresponde a ordem
    das imagens em `cxr_test.npy`, o que permite ligar cada caso a sua
    radiografia real pelo indice.
    """
    fonte = fonte or config.diretorio_fonte()
    test = pd.read_csv(fonte / "test.csv")
    positivos = test[test["label"] == 1].reset_index(drop=True)
    return positivos


def dados_clinicos_por_admissao(fonte: Path | None = None) -> pd.DataFrame:
    """
    Tabela com os dados demograficos e clinicos, indexada por `hadm_id`.

    Apenas o `symile_mimic_data.csv` (base antes do split) carrega idade, sexo,
    raca, dados da admissao e os 14 achados do CheXpert.
    """
    fonte = fonte or config.diretorio_fonte()
    completo = pd.read_csv(fonte / "symile_mimic_data.csv", low_memory=False)
    tabela = completo.set_index("hadm_id")

    # Com hadm_id repetido, `.loc[hadm_id]` devolveria um DataFrame em vez de uma
    # Series e o erro so apareceria la na frente, como "truth value is ambiguous".
    duplicados = tabela.index.duplicated()
    if duplicados.any():
        exemplos = tabela.index[duplicados].unique()[:3].tolist()
        raise ValueError(
            f"symile_mimic_data.csv tem {duplicados.sum()} hadm_id repetidos "
            f"(ex.: {exemplos}); esperava uma linha por admissao."
        )
    return tabela
