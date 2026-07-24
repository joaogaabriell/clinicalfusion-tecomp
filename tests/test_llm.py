"""Testes da camada LLM: relatorio, prompt, base e catalogo."""

import base64
import io

from PIL import Image

from src import config
from src.llm import base, catalogo, prompt as prompt_mod, relatorio
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
    provedores = {m.provedor for m in catalogo.CATALOGO}
    assert provedores == {"google"}
    assert len(catalogo.CATALOGO) >= 1


def test_selecionar_padrao_retorna_gemini():
    selecionados = catalogo.selecionar()
    assert {m.provedor for m in selecionados} == {"google"}


def test_status_chaves_reporta_google():
    status = catalogo.status_chaves()
    assert set(status.keys()) == {"google"}


def _lab_vazio():
    import pandas as pd

    return pd.DataFrame(
        {"itemid": [], "exame": [], "valor": [], "percentil": [], "ausente": []}
    )


def _ecg_vazio():
    import pandas as pd

    return pd.DataFrame({"tempo_s": [0.0, 0.002], "II": [0.0, 0.1]})
