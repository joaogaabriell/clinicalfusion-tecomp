"""Testes da augmentation das radiografias reais."""

import numpy as np
import pandas as pd

from src import augmentation, build_subset, config, loaders, mock


def _subset_com_cxr_real(tmp_path, caso_bruto, caso_clinico) -> "Path":
    """Monta um subconjunto minimo com uma radiografia marcada como real."""
    imagem = mock.gerar_cxr_placeholder("patient_0001")  # so precisa de uma imagem
    linha = build_subset._escrever_paciente(
        tmp_path, "patient_0001", caso_bruto, caso_clinico, imagem, cxr_real=True
    )
    pd.DataFrame([linha]).to_csv(tmp_path / "index.csv", index=False)
    return tmp_path


def test_aplicar_preserva_tamanho_e_modo():
    original = mock.gerar_cxr_placeholder("patient_0001")
    parametros = augmentation.ParametrosAug(
        rotacao_graus=5, brilho=1.1, contraste=0.9, gama=1.05, zoom=1.05, ruido_std=0.01
    )
    saida = augmentation.aplicar(original, parametros)

    assert saida.size == (config.CXR_LADO, config.CXR_LADO)
    assert saida.mode == "RGB"


def test_variacoes_incluem_original_mais_n(tmp_path, caso_bruto, caso_clinico):
    base = _subset_com_cxr_real(tmp_path, caso_bruto, caso_clinico)
    variacoes = augmentation.variacoes_de("patient_0001", n_variacoes=3, base=base)

    assert len(variacoes) == 4  # original + 3 variacoes
    ids = [v[0] for v in variacoes]
    assert ids[0] == "patient_0001"
    assert ids[1:] == ["patient_0001_aug1", "patient_0001_aug2", "patient_0001_aug3"]
    assert variacoes[0][2] is None  # original nao tem parametros


def test_variacao_difere_da_original(tmp_path, caso_bruto, caso_clinico):
    base = _subset_com_cxr_real(tmp_path, caso_bruto, caso_clinico)
    variacoes = augmentation.variacoes_de("patient_0001", n_variacoes=1, base=base)

    original = np.asarray(variacoes[0][1], dtype=np.int16)
    aumentada = np.asarray(variacoes[1][1], dtype=np.int16)
    assert original.shape == aumentada.shape
    assert np.abs(original - aumentada).mean() > 0  # a transformacao mudou algo


def test_variacoes_sao_reprodutiveis(tmp_path, caso_bruto, caso_clinico):
    """Sem determinismo, o conjunto aumentado mudaria a cada geracao."""
    base = _subset_com_cxr_real(tmp_path, caso_bruto, caso_clinico)
    a = augmentation.variacoes_de("patient_0001", n_variacoes=2, base=base)
    b = augmentation.variacoes_de("patient_0001", n_variacoes=2, base=base)

    for (_, img_a, _), (_, img_b, _) in zip(a, b):
        assert np.array_equal(np.asarray(img_a), np.asarray(img_b))


def test_gerar_conjunto_so_inclui_cxr_real(tmp_path, caso_bruto, caso_clinico):
    base = _subset_com_cxr_real(tmp_path, caso_bruto, caso_clinico)
    destino = tmp_path / "aug"
    indice = augmentation.gerar_conjunto_aumentado(
        n_variacoes=2, base=base, destino=destino
    )

    # 1 caso real x (original + 2 variacoes) = 3 imagens.
    assert len(indice) == 3
    assert indice["e_original"].sum() == 1
    assert (destino / "patient_0001_aug1" / augmentation.ARQUIVO_CXR_AUG).is_file()
