"""Testes da leitura do subconjunto — o item 3 da entrega da Semana 1."""

import pytest

from src import config, loaders


def test_carrega_as_quatro_modalidades(subconjunto):
    caso = loaders.carregar_caso("patient_0001", base=subconjunto)

    assert caso.radiografia.size == (config.CXR_LADO, config.CXR_LADO)
    assert caso.ecg.shape == (config.ECG_N_AMOSTRAS, len(config.ECG_DERIVACOES) + 1)
    assert len(caso.laboratorio) == 50
    assert caso.dados_clinicos["demografia"]["idade"] == 67


def test_ecg_traz_as_doze_derivacoes(subconjunto):
    ecg = loaders.carregar_ecg("patient_0001", base=subconjunto)

    assert [c for c in ecg.columns if c != "tempo_s"] == config.ECG_DERIVACOES


def test_laboratorio_le_ausentes_como_booleano(subconjunto):
    """O round-trip pelo CSV precisa devolver bool, nao a string "False"."""
    laboratorio = loaders.carregar_laboratorio("patient_0001", base=subconjunto)

    assert laboratorio["ausente"].dtype == bool


def test_exames_presentes_descarta_os_ausentes(subconjunto):
    laboratorio = loaders.carregar_laboratorio("patient_0001", base=subconjunto)

    presentes = loaders.exames_presentes(laboratorio)

    assert len(presentes) == 47
    assert not presentes["ausente"].any()


def test_caso_expoe_a_proveniencia(subconjunto):
    caso = loaders.carregar_caso("patient_0001", base=subconjunto)

    assert caso.tem_radiografia_real is False
    assert caso.proveniencia["ecg"] == "mock"


def test_indice_lista_os_pacientes(subconjunto):
    indice = loaders.listar_pacientes(base=subconjunto)

    assert list(indice["paciente_id"]) == ["patient_0001"]


def test_paciente_inexistente_falha_com_mensagem_clara(subconjunto):
    with pytest.raises(FileNotFoundError, match="Paciente desconhecido"):
        loaders.carregar_caso("patient_9999", base=subconjunto)


def test_subconjunto_ausente_orienta_a_gerar(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_subset"):
        loaders.listar_pacientes(base=tmp_path / "nao_existe")
