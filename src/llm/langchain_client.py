"""
Orquestracao do LLM multimodal via LangChain.

`ClienteLangChain` fala com o Gemini pelo chat model do LangChain
(ChatGoogleGenerativeAI). A mensagem multimodal (system + texto + imagem) e
montada no formato comum do LangChain e enviada com `chat.invoke` -- essa e a
orquestracao que o LangChain nos da: o formato da mensagem e da resposta nao
depende do SDK do provedor.

O projeto usa APENAS o Gemini (decisao da equipe, ver src/llm/catalogo.py). Os
ramos de OpenAI e Anthropic foram removidos daqui: enquanto nao forem usados,
mante-los significava tres caminhos de codigo sem cobertura de teste ao vivo.
Para reativar um deles, adicionar a entrada em `_INTEGRACAO`, o ramo
correspondente em `_construir_chat` (ChatOpenAI / ChatAnthropic) e a linha em
`ENV_POR_PROVEDOR` no catalogo -- o resto da classe e provider-agnostico.

Mantem a fachada `ClienteLLM.gerar` / `RelatorioClinico`, entao benchmark,
interface e testes nao mudam. A chave vem do ambiente (via .env carregado por
config.carregar_env); nao e lida aqui explicitamente, exceto para checar
presenca e falhar cedo com uma mensagem clara.

Os pacotes do LangChain sao importados de forma preguicosa para que importar
este modulo (e o catalogo) funcione mesmo sem eles instalados.
"""

import time

from .. import config
from .base import ClienteLLM, ErroLLM, RespostaLLM, com_retry
from .prompt import PromptMultimodal

# Pacote de integracao LangChain e variavel de ambiente por provedor.
_INTEGRACAO = {
    "google": ("langchain_google_genai", "GOOGLE_API_KEY"),
}

# Modelos que REJEITAM thinking_budget=0. O parametro e aceito na construcao do
# chat model (nao levanta TypeError) e so estoura na chamada, como
# "400 INVALID_ARGUMENT: Request contains an invalid argument" -- uma mensagem
# generica, que nao diz qual argumento e o culpado. Verificado em 2026-07-31:
# com o parametro o gemini-3.5-flash-lite falha em 100% das chamadas; sem ele,
# responde normalmente. Se um modelo novo comecar a dar 400 sem motivo aparente,
# testar primeiro tirando o thinking_budget e, se resolver, incluir aqui.
_REJEITAM_THINKING_BUDGET = {"gemini-3.5-flash-lite"}


class ClienteLangChain(ClienteLLM):
    """Cliente do Gemini, orquestrado pelo LangChain."""

    def __init__(self, provedor: str, modelo: str, max_tokens: int = 2000):
        super().__init__(modelo)
        if provedor not in _INTEGRACAO:
            raise ErroLLM(f"Provedor sem integracao LangChain: {provedor}")
        self.provedor = provedor
        self._max_tokens = max_tokens

        config.carregar_env()  # garante que a chave do .env esteja no ambiente
        pacote, env_var = _INTEGRACAO[provedor]
        import os

        if not os.environ.get(env_var):
            raise ErroLLM(f"Defina {env_var} para usar o provedor '{provedor}'.")

        self._chat = self._construir_chat(provedor, modelo, max_tokens)

    @staticmethod
    def _construir_chat(provedor: str, modelo: str, max_tokens: int):
        """Constroi o chat model do LangChain do provedor (import preguicoso)."""
        if provedor != "google":
            raise ErroLLM(f"Provedor sem integracao LangChain: {provedor}")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - depende de instalacao
            pacote, _ = _INTEGRACAO[provedor]
            raise ErroLLM(
                f"Pacote '{pacote.replace('_', '-')}' nao instalado. "
                f"Rode: pip install {pacote.replace('_', '-')}"
            ) from exc

        # max_retries=1 desliga o retry interno do LangChain (padrao 6):
        # com_retry() ja repete 4 vezes por fora. Manter o retry interno no
        # minimo evita uma cascata de chamadas quando o provedor devolve 503.
        opcoes = {"model": modelo, "max_output_tokens": max_tokens, "max_retries": 1}
        if modelo in _REJEITAM_THINKING_BUDGET:
            return ChatGoogleGenerativeAI(**opcoes)

        # thinking_budget=0 evita que o raciocinio do Gemini 3.x consuma
        # o orcamento de saida e trunque o JSON.
        try:
            return ChatGoogleGenerativeAI(thinking_budget=0, **opcoes)
        except TypeError:  # versao do pacote sem o parametro thinking_budget
            return ChatGoogleGenerativeAI(**opcoes)

    def gerar(self, prompt: PromptMultimodal, max_tokens: int = 2000) -> RespostaLLM:
        from langchain_core.messages import HumanMessage, SystemMessage

        inicio = time.perf_counter()
        url_imagem = f"data:image/png;base64,{self.imagem_para_base64(prompt.imagem)}"
        mensagens = [
            SystemMessage(content=prompt.system),
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt.texto},
                    {"type": "image_url", "image_url": {"url": url_imagem}},
                ]
            ),
        ]
        try:
            resposta = com_retry(lambda: self._chat.invoke(mensagens))
        except Exception as exc:
            return RespostaLLM(
                modelo=self.modelo,
                provedor=self.provedor,
                relatorio=None,
                texto_bruto="",
                latencia_s=time.perf_counter() - inicio,
                erro=f"falha na chamada: {exc}",
            )

        texto = _texto_da_resposta(resposta)
        uso = getattr(resposta, "usage_metadata", None) or {}
        return self._finalizar(
            texto,
            inicio,
            tokens_entrada=uso.get("input_tokens"),
            tokens_saida=uso.get("output_tokens"),
        )

    def conversar(self, system: str, texto: str) -> str:
        """Chamada apenas-texto (sem imagem), para tarefas como reescrita."""
        from langchain_core.messages import HumanMessage, SystemMessage

        resposta = com_retry(
            lambda: self._chat.invoke(
                [SystemMessage(content=system), HumanMessage(content=texto)]
            )
        )
        return _texto_da_resposta(resposta)

    def chat_caso(self, system, contexto, imagem, historico, pergunta):
        """
        Conversa sobre um caso (modo chat, sem JSON forcado).

        O caso (dados/labs/ECG/achados) vai no system como texto. A imagem so e
        enviada quando `imagem` nao e None -- omiti-la economiza ~1.300 tokens por
        pergunta (o chat responde sobre a radiografia pelos achados CheXpert
        rotulados que ja estao no contexto). O historico e uma lista de dicts
        {"role": "user"|"assistant", "content": str}.

        Returns:
            (texto, tokens_entrada, tokens_saida).
        """
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        mensagens = [
            SystemMessage(content=f"{system}\n\n== Caso clinico ==\n{contexto}")
        ]
        if imagem is not None:
            url = f"data:image/png;base64,{self.imagem_para_base64(imagem)}"
            mensagens.append(
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Radiografia do caso em anexo."},
                        {"type": "image_url", "image_url": {"url": url}},
                    ]
                )
            )
            mensagens.append(AIMessage(content="Analisei o caso; pode perguntar."))
        for turno in historico:
            classe = HumanMessage if turno["role"] == "user" else AIMessage
            mensagens.append(classe(content=turno["content"]))
        mensagens.append(HumanMessage(content=pergunta))

        resposta = com_retry(lambda: self._chat.invoke(mensagens))
        uso = getattr(resposta, "usage_metadata", None) or {}
        return (
            _texto_da_resposta(resposta),
            uso.get("input_tokens"),
            uso.get("output_tokens"),
        )


def _texto_da_resposta(mensagem) -> str:
    """Extrai o texto de uma AIMessage (content pode ser str ou lista de blocos)."""
    conteudo = getattr(mensagem, "content", "")
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = []
        for bloco in conteudo:
            if isinstance(bloco, dict):
                partes.append(bloco.get("text", ""))
            else:
                partes.append(str(bloco))
        return "".join(partes)
    return str(conteudo)
