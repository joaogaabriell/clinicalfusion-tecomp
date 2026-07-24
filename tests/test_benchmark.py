"""Testes do benchmark: metricas e orquestrador (offline, sem chamar APIs)."""

import pandas as pd

from src import build_subset, mock
from src.benchmark import metricas, runner
from src.llm import catalogo
from src.llm.base import ClienteLLM, RespostaLLM
from src.llm.relatorio import RelatorioClinico


# --- fixture local: subconjunto com uma radiografia real ------------------


def _subset_real(tmp_path, caso_bruto, caso_clinico):
    imagem = mock.gerar_cxr_placeholder("patient_0001")
    linha = build_subset._escrever_paciente(
        tmp_path, "patient_0001", caso_bruto, caso_clinico, imagem, cxr_real=True
    )
    pd.DataFrame([linha]).to_csv(tmp_path / "index.csv", index=False)
    return tmp_path


# --- ground truth ---------------------------------------------------------


def test_ground_truth_so_pega_positivo_e_negativo():
    dados = {
        "radiografia": {
            "achados_chexpert": {
                "Cardiomegaly": "positivo",
                "Pneumonia": "negativo",
                "Edema": "incerto",  # deve ser ignorado
            }
        }
    }
    gt = metricas.ground_truth_do_caso(dados)

    assert gt == {"Cardiomegaly": "positivo", "Pneumonia": "negativo"}


# --- avaliacao por caso ---------------------------------------------------


def _resposta(achados: dict) -> RespostaLLM:
    rel = RelatorioClinico.do_dict(
        {
            "resumo": "r",
            "achados_radiologicos": achados,
            "hipoteses": ["h"],
            "justificativa": "j",
            "exames_sugeridos": ["e"],
            "achados_principais": ["p"],
            "aviso": "a",
        }
    )
    return RespostaLLM(
        modelo="m", provedor="p", relatorio=rel, texto_bruto="{}", latencia_s=0.5
    )


def test_avaliar_caso_conta_matriz_de_confusao():
    gt = {"Cardiomegaly": "positivo", "Pneumonia": "negativo", "Edema": "positivo"}
    resposta = _resposta(
        {
            "Cardiomegaly": "positivo",  # VP
            "Pneumonia": "positivo",  # FP (era negativo)
            "Edema": "negativo",  # FN (era positivo)
        }
    )
    m = metricas.avaliar_caso(resposta, gt)

    assert m.verdadeiros_positivos == 1
    assert m.falsos_positivos == 1
    assert m.falsos_negativos == 1
    assert m.acertos == 1  # so Cardiomegaly bateu
    assert m.achados_avaliados == 3


def test_avaliar_caso_marca_falha_quando_sem_relatorio():
    resposta = RespostaLLM(
        modelo="m", provedor="p", relatorio=None, texto_bruto="", latencia_s=0.1,
        erro="resposta nao-JSON",
    )
    m = metricas.avaliar_caso(resposta, {"Pneumonia": "positivo"})

    assert m.falhou
    assert m.achados_avaliados == 0


def test_agregado_calcula_f1():
    gt = {"Pneumonia": "positivo", "Edema": "negativo"}
    m = metricas.avaliar_caso(_resposta({"Pneumonia": "positivo", "Edema": "negativo"}), gt)
    ag = metricas.agregar("m", "p", "m", [m])

    assert ag.precisao == 1.0
    assert ag.recall == 1.0
    assert ag.f1 == 1.0
    assert ag.acuracia == 1.0


# --- montar_amostras ------------------------------------------------------


def test_montar_amostras_usa_casos_com_ground_truth(tmp_path, caso_bruto, caso_clinico):
    base = _subset_real(tmp_path, caso_bruto, caso_clinico)
    amostras = runner.montar_amostras(base=base)

    assert len(amostras) == 1
    assert amostras[0].item_id == "patient_0001"
    # caso_clinico tem Cardiomegaly=positivo e Pneumonia=negativo.
    assert amostras[0].ground_truth == {
        "Cardiomegaly": "positivo",
        "Pneumonia": "negativo",
    }


# --- runner com cliente stub (sem API) ------------------------------------


class _ClienteStub(ClienteLLM):
    provedor = "stub"

    def gerar(self, prompt, max_tokens=2000):
        # Responde sempre certo para os achados do ground-truth deste teste.
        return _resposta({"Cardiomegaly": "positivo", "Pneumonia": "negativo"})


def test_rodar_modelo_gera_agregado_e_salva(tmp_path, caso_bruto, caso_clinico):
    base = _subset_real(tmp_path, caso_bruto, caso_clinico)
    amostras = runner.montar_amostras(base=base)
    candidato = catalogo.ModeloCandidato(
        "stub", "stub", "stub-1", lambda modelo: _ClienteStub(modelo)
    )
    destino = tmp_path / "resultados"
    destino.mkdir()

    agregado = runner._rodar_modelo(candidato, amostras, max_tokens=500, destino=destino)

    assert agregado is not None
    assert agregado.f1 == 1.0
    assert agregado.n_falhas == 0
    assert (destino / "respostas_stub.json").is_file()
