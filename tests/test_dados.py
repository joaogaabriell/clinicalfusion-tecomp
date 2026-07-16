"""Testes da ponte entre a interface e o subconjunto."""

import pandas as pd
import pytest

import dados
from src import loaders


@pytest.fixture
def laboratorio(subconjunto):
    return loaders.carregar_laboratorio("patient_0001", base=subconjunto)


@pytest.fixture
def clinicos(subconjunto):
    return loaders.carregar_dados_clinicos("patient_0001", base=subconjunto)


def test_tabela_laboratorio_tem_as_colunas_da_tela(laboratorio):
    tabela = dados.tabela_laboratorio(laboratorio)

    assert list(tabela.columns) == ["Exame", "Valor", "Percentil", "Situação"]
    assert len(tabela) == 50


def test_percentil_vira_porcentagem(laboratorio):
    tabela = dados.tabela_laboratorio(laboratorio)

    assert tabela["Percentil"].dropna().between(0, 100).all()


def test_exame_nao_medido_e_marcado(laboratorio):
    tabela = dados.tabela_laboratorio(laboratorio)

    assert (tabela["Situação"] == "Não medido").sum() == 3


@pytest.mark.parametrize(
    "percentil, esperado",
    [
        (0.02, "Percentil baixo"),
        (0.5, "Faixa central"),
        (0.98, "Percentil alto"),
        (0.05, "Percentil baixo"),
        (0.95, "Percentil alto"),
    ],
)
def test_situacao_classifica_pelas_caudas(percentil, esperado):
    linha = pd.Series({"ausente": False, "percentil": percentil})

    assert dados._situacao(linha) == esperado


def test_exames_extremos_ignora_a_faixa_central():
    tabela = pd.DataFrame(
        {
            "Exame": ["a", "b", "c", "d"],
            "Situação": [
                "Percentil baixo",
                "Faixa central",
                "Percentil alto",
                "Não medido",
            ],
        }
    )

    extremos = dados.exames_extremos(tabela)

    assert list(extremos["Exame"]) == ["a", "c"]


def test_dias_internado_usa_as_datas_reais(clinicos):
    """A fixture vai de 2150-01-01 10:00 a 2150-01-08 14:00."""
    assert dados.dias_internado(clinicos) == 7


def test_dias_internado_sem_alta_devolve_none(clinicos):
    clinicos["admissao"]["alta_em"] = None

    assert dados.dias_internado(clinicos) is None


def test_achados_positivos_filtra_negativos_e_incertos(clinicos):
    """A fixture tem Cardiomegaly positivo, Pneumonia negativo e Edema incerto."""
    assert dados.achados_positivos(clinicos) == ["Cardiomegaly"]


def test_tabela_achados_lista_o_que_foi_mencionado(clinicos):
    tabela = dados.tabela_achados(clinicos)

    assert list(tabela.columns) == ["Achado", "CheXpert"]
    assert len(tabela) == 3


def test_tabela_achados_vazia_nao_quebra():
    tabela = dados.tabela_achados({"radiografia": {"achados_chexpert": {}}})

    assert tabela.empty


@pytest.mark.parametrize(
    "sigla, esperado", [("M", "Masculino"), ("F", "Feminino"), (None, "—")]
)
def test_sexo_extenso(sigla, esperado):
    assert dados.sexo_extenso(sigla) == esperado


def test_rotulo_paciente_mostra_sexo_e_idade():
    indice = pd.DataFrame([{"paciente_id": "patient_0001", "sexo": "F", "idade": 61}])

    assert dados.rotulo_paciente("patient_0001", indice) == "patient_0001 — F, 61 anos"


def test_rotulo_paciente_sem_idade_nao_mostra_none():
    """Sem guard, a f-string exibiria o literal "None anos" no seletor."""
    indice = pd.DataFrame(
        [{"paciente_id": "patient_0001", "sexo": None, "idade": float("nan")}]
    )

    assert dados.rotulo_paciente("patient_0001", indice) == "patient_0001 — —, —"


@pytest.mark.parametrize("valor", [None, float("nan")])
def test_texto_troca_ausente_por_travessao(valor):
    assert dados.texto(valor) == "—"
    assert dados.texto(valor, " anos") == "—"


def test_texto_nao_deixa_float_inteiro_com_casa_decimal():
    """A idade vem do CSV como float; `61.0 anos` ficaria feio na tela."""
    assert dados.texto(61.0, " anos") == "61 anos"


def test_idade_texto_sem_o_campo():
    assert dados.idade_texto({}) == "—"
