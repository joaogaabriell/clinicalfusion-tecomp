"""
Camada de integracao com LLMs multimodais para o ClinicalFusion.

Fronteira unica entre a aplicacao (interface, benchmark) e os provedores. O
resto do codigo enxerga sempre a mesma interface (`ClienteLLM`), independentemente
de o provedor ser OpenAI, Google ou Anthropic -- trocar de modelo nao muda
nenhuma assinatura.
"""

from .base import ClienteLLM, RespostaLLM, ErroLLM
from .relatorio import RelatorioClinico, VALOR_ACHADO

__all__ = [
    "ClienteLLM",
    "RespostaLLM",
    "ErroLLM",
    "RelatorioClinico",
    "VALOR_ACHADO",
]
