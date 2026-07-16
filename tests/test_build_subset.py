"""Testes da montagem do subconjunto por paciente."""

import numpy as np
import pytest

from src import build_subset, config


def test_laboratorio_lista_os_cinquenta_exames(caso_bruto):
    """Os exames ausentes continuam na tabela: a ausencia e um dado."""
    tabela = build_subset._tabela_laboratorio(caso_bruto)

    assert len(tabela) == 50
    assert list(tabela["itemid"]) == list(config.LABS)


def test_laboratorio_marca_exame_ausente(caso_bruto):
    tabela = build_subset._tabela_laboratorio(caso_bruto)
    ausentes = tabela[tabela["ausente"]]

    assert len(ausentes) == 3
    assert ausentes["valor"].isna().all()


def test_laboratorio_preserva_o_valor_real(caso_bruto):
    tabela = build_subset._tabela_laboratorio(caso_bruto)
    hematocrito = tabela[tabela["itemid"] == "51221"].iloc[0]

    assert hematocrito["exame"] == "Hematocrit"
    assert hematocrito["valor"] == 10.0
    assert not hematocrito["ausente"]


def test_achados_omitem_o_que_nao_foi_mencionado(caso_clinico):
    """NaN no CheXpert significa achado nao citado no laudo, nao ausencia dele."""
    achados = build_subset._achados_chexpert(caso_clinico)

    assert achados == {
        "Cardiomegaly": "positivo",
        "Edema": "incerto",
        "Pneumonia": "negativo",
    }


def test_dados_clinicos_registram_proveniencia_de_cada_modalidade(
    caso_bruto, caso_clinico
):
    dados = build_subset._dados_clinicos(
        "patient_0001", caso_bruto, caso_clinico, cxr_real=True
    )

    assert dados["_proveniencia"]["radiografia"] == "real"
    assert dados["_proveniencia"]["ecg"] == "mock"
    assert dados["_proveniencia"]["laboratorio"] == "real"


def test_dados_clinicos_marcam_radiografia_mock(caso_bruto, caso_clinico):
    dados = build_subset._dados_clinicos(
        "patient_0001", caso_bruto, caso_clinico, cxr_real=False
    )

    assert dados["_proveniencia"]["radiografia"] == "mock"


def test_dados_clinicos_trazem_a_demografia_real(caso_bruto, caso_clinico):
    dados = build_subset._dados_clinicos(
        "patient_0001", caso_bruto, caso_clinico, cxr_real=True
    )

    assert dados["demografia"] == {"idade": 67, "sexo": "M", "raca": "WHITE"}
    assert dados["subject_id"] == 10000001
    assert dados["hadm_id"] == 20000001


def test_obito_hospitalar_vira_booleano(caso_bruto, caso_clinico):
    """`hospital_expire_flag` e 0/1; bool() direto sobre a string "0" daria True."""
    caso_clinico["hospital_expire_flag"] = "0"

    dados = build_subset._dados_clinicos(
        "patient_0001", caso_bruto, caso_clinico, cxr_real=True
    )

    assert dados["admissao"]["obito_hospitalar"] is False


def test_ecg_gerado_cobre_os_dez_segundos():
    tabela = build_subset._tabela_ecg("patient_0001")

    assert len(tabela) == config.ECG_N_AMOSTRAS
    assert list(tabela.columns) == ["tempo_s", *config.ECG_DERIVACOES]
    assert np.isclose(
        tabela["tempo_s"].iloc[-1], config.ECG_DURACAO_S - 1 / config.ECG_FREQUENCIA_HZ
    )


@pytest.mark.parametrize("n_casos", [99, 501, 0])
def test_construir_recusa_quantidade_fora_do_enunciado(n_casos):
    with pytest.raises(ValueError, match="casos"):
        build_subset.construir(n_casos=n_casos)


def test_conferir_colunas_aceita_o_schema_esperado(caso_bruto):
    build_subset._conferir_colunas_de_exame(caso_bruto.to_frame().T)


def test_conferir_colunas_denuncia_exame_faltando(caso_bruto):
    """
    Sem esta checagem, uma coluna com nome diferente passaria por Series.get()
    como None e o exame viraria "nao medido" em todos os pacientes.
    """
    casos = caso_bruto.to_frame().T.drop(columns=["51221"])

    with pytest.raises(ValueError, match="colunas de exame"):
        build_subset._conferir_colunas_de_exame(casos)
