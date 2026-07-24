"""
Construcao do prompt multimodal a partir de um Caso (RF07).

Unifica as quatro modalidades em uma unica instrucao: dados clinicos + demografia
+ exames laboratoriais medidos + a radiografia (imagem) + a pergunta do usuario.
O ECG e mock no material disponibilizado, entao ele NAO entra no prompt como se
fosse sinal real -- deixamos isso explicito para o modelo nao inventar laudo de
ECG. A saida pedida e sempre o JSON do relatorio estruturado (ver relatorio.py).

O prompt e provider-agnostico: devolve um `PromptMultimodal` com system, texto e
imagem separados; cada cliente (OpenAI/Gemini/Anthropic) codifica a imagem no
formato que a sua API espera.
"""

from dataclasses import dataclass

from PIL import Image

from .. import config, loaders
from . import relatorio


@dataclass
class PromptMultimodal:
    """Prompt pronto para envio, ainda independente de provedor."""

    system: str
    texto: str
    imagem: Image.Image
    tem_radiografia_real: bool


SYSTEM = (
    "Voce e um assistente clinico multimodal de apoio EDUCACIONAL. Voce integra "
    "radiografia de torax, exames laboratoriais e dados clinicos de um mesmo "
    "paciente para produzir um relatorio estruturado. Voce NAO emite diagnostico "
    "definitivo nem substitui avaliacao medica. Baseie cada conclusao nas "
    "evidencias apresentadas e assuma incerteza quando os dados forem "
    "insuficientes.\n\n"
    "Responda SEMPRE com um unico objeto JSON valido, sem texto fora do JSON e "
    "sem cercas de codigo. O JSON deve conter exatamente estas chaves: "
    "resumo (string), achados_radiologicos (objeto), achados_principais (lista de "
    "strings), hipoteses (lista de strings), justificativa (string), "
    "exames_sugeridos (lista de strings) e aviso (string).\n\n"
    "Em achados_radiologicos, avalie a radiografia para cada um dos 14 achados do "
    "CheXpert e atribua exatamente um valor: 'positivo' (presente), 'negativo' "
    "(ausente) ou 'indeterminado' (nao avaliavel pela imagem). Os 14 achados sao: "
    + ", ".join(config.ACHADOS_CHEXPERT)
    + ".\n\n"
    "IDIOMA: escreva TODO o conteudo textual do relatorio em portugues do Brasil "
    "(resumo, achados_principais, hipoteses, justificativa, exames_sugeridos, "
    "aviso). Os dados de entrada vem em ingles (raca, tipo de admissao, nomes de "
    "exames laboratoriais, achados radiologicos) -- traduza esses termos para o "
    "portugues ao mencionA-los no texto. UNICA excecao: as CHAVES do objeto "
    "achados_radiologicos devem permanecer EXATAMENTE com os nomes em ingles do "
    "CheXpert listados acima (sao identificadores, nao traduza nem altere)."
)


def _formatar_laboratorio(laboratorio) -> str:
    """Lista os exames efetivamente medidos, com valor e percentil."""
    medidos = loaders.exames_presentes(laboratorio)
    if medidos.empty:
        return "Nenhum exame laboratorial medido para este caso."
    linhas = []
    for _, ex in medidos.iterrows():
        percentil = ex.get("percentil")
        sufixo = f" (percentil {percentil})" if percentil == percentil else ""
        linhas.append(f"- {ex['exame']}: {ex['valor']}{sufixo}")
    return "\n".join(linhas)


def _formatar_clinico(dados: dict) -> str:
    """Demografia e admissao em texto compacto."""
    demo = dados.get("demografia", {})
    adm = dados.get("admissao", {})
    partes = [
        f"Idade: {demo.get('idade', 'n/d')}",
        f"Sexo: {demo.get('sexo', 'n/d')}",
        f"Raca: {demo.get('raca', 'n/d')}",
        f"Tipo de admissao: {adm.get('tipo', 'n/d')}",
        f"Origem: {adm.get('origem', 'n/d')}",
        f"Desfecho: {adm.get('desfecho', 'n/d')}",
    ]
    return "\n".join(partes)


def _resumo_ecg(ecg) -> str:
    """Descricao fatual do tracado de ECG (formato), sem inventar laudo."""
    derivacoes = [c for c in ecg.columns if c != "tempo_s"]
    duracao = float(ecg["tempo_s"].iloc[-1]) if len(ecg) else 0.0
    return (
        f"Tracado de {len(derivacoes)} derivacoes ({', '.join(derivacoes)}), "
        f"{len(ecg)} amostras cobrindo {duracao:.0f} s "
        f"({config.ECG_FREQUENCIA_HZ} Hz)."
    )


def montar_prompt(caso: loaders.Caso, pergunta: str | None = None) -> PromptMultimodal:
    """
    Monta o prompt multimodal para um caso, opcionalmente com pergunta do usuario.

    A imagem entra como anexo (via cliente); aqui montamos apenas o texto que a
    acompanha e o system prompt.
    """
    clinico = _formatar_clinico(caso.dados_clinicos)
    labs = _formatar_laboratorio(caso.laboratorio)

    aviso_cxr = (
        "A radiografia anexada e real."
        if caso.tem_radiografia_real
        else (
            "ATENCAO: a imagem anexada e um PLACEHOLDER (a radiografia real nao "
            "esta disponivel para este caso). Marque os achados radiologicos como "
            "'indeterminado'."
        )
    )
    bloco_pergunta = (
        f"\n\nPergunta do usuario: {pergunta.strip()}\n"
        "Enderece a pergunta no campo 'resumo' e na 'justificativa'."
        if pergunta and pergunta.strip()
        else ""
    )

    ecg_resumo = _resumo_ecg(caso.ecg)
    texto = (
        "Caso clinico para analise integrada das QUATRO modalidades.\n\n"
        f"== 1. Dados clinicos ==\n{clinico}\n\n"
        f"== 2. Exames laboratoriais medidos ==\n{labs}\n\n"
        f"== 3. Radiografia de torax ==\n{aviso_cxr}\n\n"
        f"== 4. Eletrocardiograma (ECG) ==\n{ecg_resumo}\n"
        "ATENCAO: este ECG e SINTETICO (mock) -- o material disponibilizado nao "
        "traz os sinais reais. Considere-o apenas como a modalidade presente no "
        "caso; NAO produza laudo eletrocardiografico nem baseie hipoteses "
        "cardiologicas nele."
        f"{bloco_pergunta}\n\n"
        "Produza agora o relatorio estruturado em JSON."
    )

    return PromptMultimodal(
        system=SYSTEM,
        texto=texto,
        imagem=caso.radiografia.convert("RGB"),
        tem_radiografia_real=caso.tem_radiografia_real,
    )


def esquema_saida() -> dict:
    """Atalho para o JSON Schema do relatorio (usado pelos clientes)."""
    return relatorio.json_schema()


def contexto_do_caso(caso: loaders.Caso) -> str:
    """
    Contexto textual do caso para o modo chat (sem pedir JSON).

    Reune dados clinicos, laboratorio medido e a nota do ECG; a radiografia vai
    como imagem anexa (nao aqui). Usado por src/llm/chat.py.
    """
    clinico = _formatar_clinico(caso.dados_clinicos)
    labs = _formatar_laboratorio(caso.laboratorio)
    proc = "real" if caso.tem_radiografia_real else "placeholder (mock)"
    achados_dict = (caso.dados_clinicos.get("radiografia", {}) or {}).get(
        "achados_chexpert", {}
    )
    positivos = [a for a, v in achados_dict.items() if str(v).lower() == "positivo"]
    negativos = [a for a, v in achados_dict.items() if str(v).lower() == "negativo"]
    return (
        f"== Dados clinicos ==\n{clinico}\n\n"
        f"== Exames laboratoriais medidos ==\n{labs}\n\n"
        f"== ECG ==\n12 derivacoes, 10 s @ {config.ECG_FREQUENCIA_HZ} Hz (SINTETICO).\n\n"
        f"== Radiografia ({proc}) ==\n"
        f"Achados CheXpert presentes: {', '.join(positivos) or 'nenhum'}. "
        f"Ausentes: {', '.join(negativos) or 'nao informado'}."
    )
