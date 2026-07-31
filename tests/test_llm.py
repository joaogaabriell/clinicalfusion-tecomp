"""Testes da camada LLM: relatorio, prompt, base e catalogo."""

import base64
import io

import pytest
from PIL import Image

from src import config
from src.llm import base, catalogo, demo_client, prompt as prompt_mod, relatorio
from src.llm.relatorio import RelatorioClinico


def test_relatorio_do_json_tolera_cerca_de_codigo():
    texto = '```json\n{"resumo": "ok", "achados_radiologicos": {}}\n```'
    rel = RelatorioClinico.do_json(texto)

    assert rel.resumo == "ok"
    # Todos os 14 achados presentes, ausentes viram "indeterminado".
    assert len(rel.achados_radiologicos) == len(config.ACHADOS_CHEXPERT)
    assert set(rel.achados_radiologicos.values()) == {"indeterminado"}


def test_relatorio_normaliza_valores_invalidos():
    dados = {"achados_radiologicos": {"Pneumonia": "talvez", "Edema": "POSITIVO"}}
    rel = RelatorioClinico.do_dict(dados)

    assert rel.achados_radiologicos["Pneumonia"] == "indeterminado"  # valor invalido
    assert rel.achados_radiologicos["Edema"] == "positivo"  # normaliza caixa


def test_relatorio_positivos_lista_apenas_presentes():
    dados = {"achados_radiologicos": {"Pneumonia": "positivo", "Edema": "negativo"}}
    rel = RelatorioClinico.do_dict(dados)

    assert rel.positivos() == ["Pneumonia"]


def test_json_schema_exige_os_14_achados():
    schema = relatorio.json_schema()
    achados = schema["properties"]["achados_radiologicos"]

    assert len(achados["required"]) == len(config.ACHADOS_CHEXPERT)
    assert achados["additionalProperties"] is False


def test_prompt_avisa_quando_radiografia_e_placeholder():
    class CasoFake:
        radiografia = Image.new("RGB", (320, 320))
        laboratorio = _lab_vazio()
        ecg = _ecg_vazio()
        dados_clinicos = {"demografia": {}, "admissao": {}, "radiografia": {}}
        tem_radiografia_real = False

    p = prompt_mod.montar_prompt(CasoFake())

    assert "PLACEHOLDER" in p.texto
    assert not p.tem_radiografia_real
    assert "CheXpert" in p.system or "achados" in p.system.lower()


def test_prompt_inclui_pergunta_do_usuario():
    class CasoFake:
        radiografia = Image.new("RGB", (320, 320))
        laboratorio = _lab_vazio()
        ecg = _ecg_vazio()
        dados_clinicos = {"demografia": {}, "admissao": {}, "radiografia": {}}
        tem_radiografia_real = True

    p = prompt_mod.montar_prompt(CasoFake(), pergunta="Ha sinais de pneumonia?")

    assert "pneumonia" in p.texto.lower()


def test_imagem_para_base64_roundtrip():
    original = Image.new("RGB", (8, 8), (200, 100, 50))
    b64 = base.ClienteLLM.imagem_para_base64(original)
    recuperada = Image.open(io.BytesIO(base64.standard_b64decode(b64)))

    assert recuperada.size == (8, 8)


def test_catalogo_usa_apenas_gemini():
    # "demo" nao e provedor de API (relatorio simulado, ver demo_client.py):
    # a decisao da equipe vale para os provedores que consomem chave.
    provedores = {m.provedor for m in catalogo.CATALOGO if m.provedor != "demo"}
    assert provedores == {"google"}
    assert len(catalogo.CATALOGO) >= 1


def test_selecionar_padrao_retorna_gemini():
    selecionados = catalogo.selecionar()
    assert {m.provedor for m in selecionados} == {"google"}


def test_demo_fica_fora_do_benchmark_padrao():
    """O cliente simulado nunca pode entrar numa comparacao de modelos."""
    assert "demo" not in catalogo.CHAVES_PADRAO


def test_status_chaves_reporta_google():
    status = catalogo.status_chaves()
    assert set(status.keys()) == {"google", "demo"}


def _lab_vazio():
    import pandas as pd

    return pd.DataFrame(
        {"itemid": [], "exame": [], "valor": [], "percentil": [], "ausente": []}
    )


def _ecg_vazio():
    import pandas as pd

    return pd.DataFrame({"tempo_s": [0.0, 0.002], "II": [0.0, 0.1]})


# --- Cliente de demonstracao ----------------------------------------------


def _prompt_demo(tem_radiografia_real=True, pergunta="Quais os achados?"):
    return prompt_mod.PromptMultimodal(
        system=prompt_mod.SYSTEM,
        texto=(
            "== 1. Dados clinicos ==\nIdade: 61\nSexo: F\n\n"
            "== 2. Exames laboratoriais medidos ==\n"
            "- Hematocrit: 30.1\n- Creatinine: 1.2\n\n"
            "== 3. Radiografia de torax ==\nA radiografia anexada e real.\n\n"
            f"Pergunta do usuario: {pergunta}\n"
        ),
        imagem=Image.new("RGB", (8, 8)),
        tem_radiografia_real=tem_radiografia_real,
    )


def _cliente_demo(monkeypatch):
    """Cliente de demonstracao sem a pausa artificial, para o teste correr rapido."""
    monkeypatch.setattr(demo_client, "_ATRASO_S", 0)
    return demo_client.ClienteDemonstracao()


def test_demo_gera_relatorio_valido(monkeypatch):
    resposta = _cliente_demo(monkeypatch).gerar(_prompt_demo())

    assert resposta.ok
    assert resposta.provedor == "demo"
    # Passa pelo mesmo parser dos clientes reais: 14 achados sempre presentes.
    assert len(resposta.relatorio.achados_radiologicos) == len(config.ACHADOS_CHEXPERT)


def test_demo_marca_todo_texto_como_simulado(monkeypatch):
    """A marca e a unica coisa que impede confundir a demo com um laudo real."""
    rel = _cliente_demo(monkeypatch).gerar(_prompt_demo()).relatorio

    assert "[SIMULADO]" in rel.resumo
    assert "[SIMULADO]" in rel.aviso
    assert all("[SIMULADO]" in h for h in rel.hipoteses)


def test_demo_e_deterministico(monkeypatch):
    """Mesmo caso, mesmo relatorio -- a tela nao pode mudar durante a apresentacao."""
    cliente = _cliente_demo(monkeypatch)
    primeira = cliente.gerar(_prompt_demo()).relatorio
    segunda = cliente.gerar(_prompt_demo()).relatorio

    assert primeira.achados_radiologicos == segunda.achados_radiologicos


def test_demo_nao_muda_achados_conforme_a_pergunta(monkeypatch):
    """Os achados sao do caso: perguntar outra coisa nao pode altera-los."""
    cliente = _cliente_demo(monkeypatch)
    uma = cliente.gerar(_prompt_demo(pergunta="Quais os achados?")).relatorio
    outra = cliente.gerar(_prompt_demo(pergunta="O que os exames mostram?")).relatorio

    assert uma.achados_radiologicos == outra.achados_radiologicos


def test_demo_sem_radiografia_real_marca_indeterminado(monkeypatch):
    rel = _cliente_demo(monkeypatch).gerar(_prompt_demo(False)).relatorio

    assert set(rel.achados_radiologicos.values()) == {"indeterminado"}


def test_thinking_budget_nao_vai_para_modelo_que_rejeita(monkeypatch):
    """
    O -lite estoura 400 se receber thinking_budget=0 (ver langchain_client.py).

    Construir o chat model nao faz chamada de rede, entao da para checar aqui.
    """
    pytest.importorskip("langchain_google_genai")
    from src.llm import langchain_client

    monkeypatch.setenv("GOOGLE_API_KEY", "chave-de-teste")
    rejeita = next(iter(langchain_client._REJEITAM_THINKING_BUDGET))

    chat = langchain_client.ClienteLangChain._construir_chat("google", rejeita, 2000)
    assert not getattr(chat, "thinking_budget", None)

    outro = langchain_client.ClienteLangChain._construir_chat(
        "google", "gemini-3.5-flash", 2000
    )
    assert getattr(outro, "thinking_budget", None) == 0


def test_demo_indisponivel_sem_variavel_de_ambiente(monkeypatch):
    """Sem CLINICALFUSION_DEMO o modo simulado nao aparece em lugar nenhum."""
    monkeypatch.delenv("CLINICALFUSION_DEMO", raising=False)
    assert not catalogo.por_chave("demo").disponivel()

    monkeypatch.setenv("CLINICALFUSION_DEMO", "1")
    assert catalogo.por_chave("demo").disponivel()
