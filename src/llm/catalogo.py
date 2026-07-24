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
from .langchain_client import ClienteLangChain


def _fabrica(provedor: str) -> Callable[[str], ClienteLLM]:
    """Fabrica um cliente LangChain para um provedor (fixa o provedor)."""
    return lambda modelo: ClienteLangChain(provedor, modelo)

# Variaveis de ambiente esperadas por provedor.
# O projeto usa apenas o Gemini (decisao da equipe). O cliente LangChain
# (langchain_client.py) continua suportando openai e anthropic -- para reativar,
# basta readicionar as linhas abaixo e as entradas correspondentes no CATALOGO.
ENV_POR_PROVEDOR = {
    "google": "GOOGLE_API_KEY",
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

# A equipe decidiu usar apenas o Gemini (Google). IMPORTANTE: cada modelo tem
# quota FREE-TIER SEPARADA (ex.: gemini-3.5-flash = 20 req/dia). Se um esgotar
# (429), troque de modelo no seletor. Os "-lite" costumam ter free-tier maior.
CATALOGO: list[ModeloCandidato] = [
    ModeloCandidato(
        "gemini-flash", "google", "gemini-3.5-flash", _fabrica("google"),
        "Melhor qualidade flash (free-tier: 20 req/dia).",
        preco_entrada=0.30, preco_saida=2.50,
    ),
    ModeloCandidato(
        "gemini-flash-lite", "google", "gemini-2.0-flash-lite", _fabrica("google"),
        "Free-tier alto -- melhor p/ testar bastante.",
        preco_entrada=0.075, preco_saida=0.30,
    ),
    ModeloCandidato(
        "gemini-2-flash", "google", "gemini-2.0-flash", _fabrica("google"),
        "Alternativa com quota propria.",
        preco_entrada=0.10, preco_saida=0.40,
    ),
    ModeloCandidato(
        "gemini-pro", "google", "gemini-pro-latest", _fabrica("google"),
        "Topo de linha do Google (exige quota; free-tier pode dar 429).",
        preco_entrada=1.25, preco_saida=10.0,
    ),
]

# Subconjunto padrao para uma comparacao rapida.
CHAVES_PADRAO = ("gemini-flash", "gemini-flash-lite")


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
