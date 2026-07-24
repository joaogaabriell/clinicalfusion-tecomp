"""
Modo chat: perguntas e respostas conversacionais sobre um caso.

Diferente do relatorio estruturado (JSON completo), aqui o usuario faz uma
pergunta especifica -- "nos exames de sangue, o que esta elevado?" -- e recebe
uma resposta DIRETA, curta e conversacional, ancorada nas evidencias do caso
(radiografia + laboratorio + dados clinicos). Mantem o historico da conversa.
"""

from . import prompt as prompt_mod

SYSTEM_CHAT = (
    "Voce e um assistente clinico de apoio EDUCACIONAL, em um chat sobre um caso "
    "especifico. Responda em portugues do Brasil, de forma DIRETA e "
    "conversacional, apenas a pergunta feita -- sem repetir o relatorio inteiro. "
    "Baseie-se nas evidencias do caso: exames laboratoriais, dados clinicos e os "
    "ACHADOS radiologicos (CheXpert) ja listados no contexto -- use esses achados "
    "para responder sobre a radiografia, mesmo sem a imagem anexa. Traduza para o "
    "portugues os termos em ingles. Se a pergunta pedir interpretacao clinica, "
    "lembre de forma breve que e educacional e nao substitui o medico. O ECG e "
    "sintetico: nao produza laudo de ECG. Se um dado nao estiver disponivel, diga "
    "isso em vez de inventar."
)


def responder(
    candidato, caso, historico: list[dict], pergunta: str, usar_imagem: bool = False
):
    """
    Responde uma pergunta do chat sobre o caso.

    Por padrao NAO envia a imagem (modo economico): a radiografia e respondida
    pelos achados CheXpert rotulados, que ja estao no contexto -- isso corta
    ~1.300 tokens por pergunta. Passe `usar_imagem=True` para analise visual real.

    Returns:
        (texto, tokens_entrada, tokens_saida).
    """
    cliente = candidato.instanciar()
    if not hasattr(cliente, "chat_caso"):
        raise TypeError("O cliente nao suporta o modo chat.")
    contexto = prompt_mod.contexto_do_caso(caso)
    imagem = caso.radiografia if usar_imagem else None
    return cliente.chat_caso(SYSTEM_CHAT, contexto, imagem, historico, pergunta)
