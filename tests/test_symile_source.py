"""
Testes da leitura do Symile-MIMIC bruto.

O dataset e credenciado e nao pode ser versionado, entao aqui simulamos o que o
disco devolveria em vez de depender dos arquivos reais.
"""

import numpy as np
import pandas as pd
import pytest

from src import config, symile_source


@pytest.fixture
def fonte_falsa(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "diretorio_fonte", lambda: tmp_path)
    return tmp_path


def _escrever_csv(tabela: pd.DataFrame, destino, nome: str):
    tabela.to_csv(destino / nome, index=False)


def test_dados_clinicos_indexa_por_admissao(fonte_falsa):
    _escrever_csv(
        pd.DataFrame({"hadm_id": [1, 2], "age": [61, 67]}),
        fonte_falsa,
        "symile_mimic_data.csv",
    )

    tabela = symile_source.dados_clinicos_por_admissao()

    assert tabela.loc[1, "age"] == 61


def test_hadm_id_repetido_falha_cedo_e_com_clareza(fonte_falsa):
    """
    Com hadm_id repetido, `.loc` devolveria um DataFrame em vez de uma Series e o
    erro so estouraria depois, como "truth value is ambiguous".
    """
    _escrever_csv(
        pd.DataFrame({"hadm_id": [1, 1, 2], "age": [61, 62, 67]}),
        fonte_falsa,
        "symile_mimic_data.csv",
    )

    with pytest.raises(ValueError, match="hadm_id repetidos"):
        symile_source.dados_clinicos_por_admissao()


def test_positivos_descartam_os_candidatos_negativos(fonte_falsa):
    _escrever_csv(
        pd.DataFrame({"hadm_id": [1, 2, 3], "label": [1, 0, 0]}),
        fonte_falsa,
        "test.csv",
    )

    positivos = symile_source.casos_positivos_do_test()

    assert list(positivos["hadm_id"]) == [1]


def test_le_apenas_as_imagens_intactas_do_tensor_truncado(fonte_falsa):
    """
    O `cxr_test.npy` que recebemos declara mais imagens do que contem; `np.load`
    falha nele. Aqui simulamos o truncamento cortando o arquivo pela metade.
    """
    destino = fonte_falsa / "data_npy" / "test"
    destino.mkdir(parents=True)
    caminho = destino / "cxr_test.npy"
    np.save(
        caminho, np.zeros((4, 3, config.CXR_LADO, config.CXR_LADO), dtype=np.float32)
    )

    bytes_por_imagem = 3 * config.CXR_LADO * config.CXR_LADO * 4
    with open(caminho, "r+b") as arquivo:
        arquivo.truncate(caminho.stat().st_size - 2 * bytes_por_imagem)

    imagens, declarado = symile_source.cxrs_recuperaveis()

    assert declarado == 4
    assert len(imagens) == 2


def test_desnormaliza_a_radiografia_para_uint8():
    """A imagem chega normalizada pela ImageNet; a tela precisa de 0–255."""
    media = np.array(config.IMAGENET_MEAN, dtype=np.float32).reshape(3, 1, 1)
    desvio = np.array(config.IMAGENET_STD, dtype=np.float32).reshape(3, 1, 1)
    cinza_medio = (np.full((3, 4, 4), 0.5, dtype=np.float32) - media) / desvio

    imagem = symile_source.cxr_para_uint8(cinza_medio)

    assert imagem.shape == (4, 4, 3)
    assert imagem.dtype == np.uint8
    assert np.allclose(imagem, 127, atol=1)


def test_desnormalizacao_satura_sem_estourar():
    """Valores fora da faixa precisam ser cortados, nao dar overflow no uint8."""
    imagem = symile_source.cxr_para_uint8(np.full((3, 2, 2), 99.0, dtype=np.float32))

    assert imagem.max() == 255
