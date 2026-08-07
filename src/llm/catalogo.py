"""
Catalogo de modelos multimodais candidatos e das chaves de API necessarias.

Ponto unico onde os modelos do benchmark sao declarados. Cada entrada diz o
provedor, o id do modelo e a variavel de ambiente que precisa estar definida.
Adicionar um modelo ao benchmark e adicionar uma linha aqui -- nada mais muda.

As chaves de API NAO ficam no repositorio: sao lidas do ambiente / do .env
(ver .env.example). Enquanto uma chave nao estiver definida, o modelo aparece
como indisponivel e o benchmark simplesmente o pula.
"""

import os
from dataclasses import dataclass
from typing import Callable

from .base import ClienteLLM
from .demo_client import ClienteDemonstracao
from .langchain_client import ClienteLangChain


def _fabrica(provedor: str) -> Callable[[str], ClienteLLM]:
    """Fabrica um cliente LangChain para um provedor (fixa o provedor)."""
    return lambda modelo: ClienteLangChain(provedor, modelo)

# Variaveis de ambiente esperadas por provedor.
# O projeto usa apenas o Gemini (decisao da equipe). Os ramos de openai e
# anthropic tambem foram removidos do cliente LangChain -- para reativar um
# deles, ver as instrucoes no topo de langchain_client.py.
#
# O provedor "demo" nao consome API: `CLINICALFUSION_DEMO` funciona como um
# interruptor, reaproveitando a regra que ja existe aqui (modelo so aparece
# quando a sua variavel esta definida). Sem a variavel, o modo demonstracao nao
# aparece em lugar nenhum -- nem na interface, nem no benchmark.
ENV_POR_PROVEDOR = {
    "google": "GOOGLE_API_KEY",
    "demo": "CLINICALFUSION_DEMO",
    # "openai": "OPENAI_API_KEY",
    # "anthropic": "ANTHROPIC_API_KEY",
}


@dataclass(frozen=True)
class ModeloCandidato:
    """Um modelo elegivel para o benchmark."""

    chave: str  # identificador curto usado na saida (ex.: "claude-opus")
    provedor: str
    modelo: str  # id real do modelo no provedor
    fabrica: Callable[[str], ClienteLLM]
    nota: str = ""
    # Preco aproximado em USD por 1M de tokens (entrada/saida). Publicos e
    # sujeitos a mudanca -- servem para estimar custo relativo no benchmark.
    preco_entrada: float = 0.0
    preco_saida: float = 0.0

    @property
    def env_var(self) -> str:
        return ENV_POR_PROVEDOR[self.provedor]

    def custo_usd(self, tokens_entrada: int | None, tokens_saida: int | None) -> float:
        """Custo estimado de uma inferencia, em USD."""
        entrada = (tokens_entrada or 0) / 1_000_000 * self.preco_entrada
        saida = (tokens_saida or 0) / 1_000_000 * self.preco_saida
        return entrada + saida

    def disponivel(self) -> bool:
        """True se a chave de API do provedor estiver definida no ambiente."""
        return bool(os.environ.get(self.env_var))

    def instanciar(self) -> ClienteLLM:
        return self.fabrica(self.modelo)


# --- Catalogo -------------------------------------------------------------
# Um representante forte por provedor + variantes de custo para comparar.

# A equipe decidiu usar apenas o Gemini (Google).
#
# Verificado em 2026-07-31: com a chave/projeto atual (conta pre-paga, com
# creditos) o gemini-3.5-flash responde normalmente. Antes disso a conta passou
# por dois estados que valem como diagnostico se o erro voltar:
#   - 403 PERMISSION_DENIED  -> o PROJETO da chave esta bloqueado para o modelo;
#     trocar de modelo nao adianta, precisa de chave em outro projeto.
#   - 429 "prepayment credits are depleted" -> chave e projeto ok, faltam
#     creditos; comprar em https://ai.studio/projects.
#   - 404 "no longer available" -> o Google APOSENTOU o modelo. Foi o que
#     aconteceu com gemini-2.0-flash e gemini-2.0-flash-lite, que estavam aqui:
#     enquanto faltavam creditos o 429 vinha antes e escondia o 404. Trocar o
#     id do modelo por um da geracao atual.
# Refazer essa verificacao ao trocar de chave. Todos os ids abaixo foram
# testados com uma chamada real em 2026-07-31.
CATALOGO: list[ModeloCandidato] = [
    ModeloCandidato(
        "gemini-flash-lite", "google", "gemini-3.5-flash-lite", _fabrica("google"),
        "Mais barato e com cota separada -- padrao do projeto.",
        preco_entrada=0.075, preco_saida=0.30,
    ),
    ModeloCandidato(
        "gemini-flash", "google", "gemini-3.5-flash", _fabrica("google"),
        "Melhor qualidade flash, sujeito a uma cota propria.",
        preco_entrada=0.30, preco_saida=2.50,
    ),
    ModeloCandidato(
        "gemini-pro", "google", "gemini-pro-latest", _fabrica("google"),
        "Topo de linha do Google.",
        preco_entrada=1.25, preco_saida=10.0,
    ),
    # NAO e um modelo: devolve um relatorio fixo, marcado como "[SIMULADO]", para
    # apresentar a interface sem chave de API (ver src/llm/demo_client.py). Fica
    # fora de CHAVES_PADRAO de proposito -- nao deve entrar em benchmark.
    ModeloCandidato(
        "demo", "demo", "relatorio-simulado", lambda modelo: ClienteDemonstracao(modelo),
        "SIMULADO -- nao chama API, so para demonstrar a interface.",
    ),
]

# Subconjunto padrao para uma comparacao rapida.
CHAVES_PADRAO = ("gemini-flash-lite", "gemini-flash")


def por_chave(chave: str) -> ModeloCandidato:
    for m in CATALOGO:
        if m.chave == chave:
            return m
    raise KeyError(f"Modelo desconhecido no catalogo: {chave}")


def selecionar(chaves: list[str] | None = None) -> list[ModeloCandidato]:
    """Resolve uma lista de chaves em candidatos (padrao: CHAVES_PADRAO)."""
    chaves = chaves or list(CHAVES_PADRAO)
    return [por_chave(c) for c in chaves]


def disponiveis(candidatos: list[ModeloCandidato] | None = None) -> list[ModeloCandidato]:
    """Filtra os candidatos cuja chave de API esta configurada."""
    candidatos = candidatos if candidatos is not None else CATALOGO
    return [m for m in candidatos if m.disponivel()]


def status_chaves() -> dict[str, bool]:
    """Diz, por provedor, se a variavel de ambiente esta definida."""
    return {prov: bool(os.environ.get(env)) for prov, env in ENV_POR_PROVEDOR.items()}
