"""
Orquestracao dos LLMs multimodais via LangChain.

Um unico cliente (`ClienteLangChain`) atende os tres provedores usando os chat
models do LangChain (ChatOpenAI, ChatGoogleGenerativeAI, ChatAnthropic). A
mensagem multimodal (system + texto + imagem) e montada uma vez no formato comum
do LangChain e a mesma invocacao (`chat.invoke`) serve para todos -- essa e a
orquestracao que o LangChain nos da: trocar de provedor e trocar a fabrica do
chat model, nada mais.

Mantem a fachada `ClienteLLM.gerar` / `RelatorioClinico`, entao benchmark,
interface e testes nao mudam. As chaves vem do ambiente (via .env carregado por
config.carregar_env); nenhuma e lida aqui explicitamente, exceto para checar
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
    "openai": ("langchain_openai", "OPENAI_API_KEY"),
    "google": ("langchain_google_genai", "GOOGLE_API_KEY"),
    "anthropic": ("langchain_anthropic", "ANTHROPIC_API_KEY"),
}


class ClienteLangChain(ClienteLLM):
    """Cliente unico para os tres provedores, orquestrado pelo LangChain."""

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
        try:
            if provedor == "openai":
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=modelo,
                    max_tokens=max_tokens,
                    model_kwargs={"response_format": {"type": "json_object"}},
                )
            if provedor == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI

                # thinking_budget=0 evita que o raciocinio do Gemini 3.x consuma
                # o orcamento de saida e trunque o JSON.
                try:
                    return ChatGoogleGenerativeAI(
                        model=modelo, max_output_tokens=max_tokens, thinking_budget=0
                    )
                except TypeError:  # versao sem o parametro thinking_budget
                    return ChatGoogleGenerativeAI(
                        model=modelo, max_output_tokens=max_tokens
                    )
            if provedor == "anthropic":
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(model=modelo, max_tokens=max_tokens)
        except ImportError as exc:  # pragma: no cover - depende de instalacao
            pacote, _ = _INTEGRACAO[provedor]
            raise ErroLLM(
                f"Pacote '{pacote.replace('_', '-')}' nao instalado. "
                f"Rode: pip install {pacote.replace('_', '-')}"
            ) from exc
        raise ErroLLM(f"Provedor sem integracao LangChain: {provedor}")

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
