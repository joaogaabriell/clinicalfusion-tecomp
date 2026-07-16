"""Testes dos geradores sinteticos das modalidades ausentes."""

import numpy as np

from src import config, mock


def test_ecg_tem_o_formato_dos_dados_reais():
    sinal = mock.gerar_ecg("patient_0001")

    assert sinal.shape == (config.ECG_N_AMOSTRAS, len(config.ECG_DERIVACOES))
    assert sinal.dtype == np.float32


def test_ecg_fica_normalizado_entre_menos_um_e_um():
    sinal = mock.gerar_ecg("patient_0001")

    assert sinal.min() >= -1.0
    assert sinal.max() <= 1.0


def test_ecg_ocupa_toda_a_faixa_de_normalizacao():
    """O pre-processamento original leva o sinal exatamente a [-1, 1]."""
    sinal = mock.gerar_ecg("patient_0001")

    assert np.isclose(sinal.min(), -1.0)
    assert np.isclose(sinal.max(), 1.0)


def test_ecg_e_reprodutivel_para_o_mesmo_paciente():
    """Sem isso, o mesmo caso mudaria de ECG a cada geracao do subconjunto."""
    assert np.array_equal(
        mock.gerar_ecg("patient_0007"), mock.gerar_ecg("patient_0007")
    )


def test_ecg_difere_entre_pacientes():
    assert not np.array_equal(
        mock.gerar_ecg("patient_0001"), mock.gerar_ecg("patient_0002")
    )


def test_ecg_tem_variacao_em_todas_as_derivacoes():
    """Uma derivacao constante indicaria um bug no fator de amplitude."""
    sinal = mock.gerar_ecg("patient_0001")

    assert np.all(sinal.std(axis=0) > 0.01)


def test_placeholder_tem_o_tamanho_das_radiografias_reais():
    imagem = mock.gerar_cxr_placeholder("patient_0100")

    assert imagem.size == (config.CXR_LADO, config.CXR_LADO)


def test_placeholder_nao_imita_uma_radiografia():
    """
    O placeholder precisa ser visivelmente artificial. Uma radiografia real tem
    ampla variacao de tons; o cartao de aviso e quase chapado.
    """
    imagem = mock.gerar_cxr_placeholder("patient_0100")

    assert np.asarray(imagem.convert("L"), dtype=np.float32).std() < 40
