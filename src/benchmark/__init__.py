"""
Ambiente de benchmark entre LLMs multimodais.

Compara os modelos do catalogo (src/llm/catalogo.py) na tarefa central do
projeto -- gerar o relatorio clinico estruturado -- pontuando objetivamente os
achados radiologicos contra o ground-truth CheXpert do dataset, alem de latencia,
custo aproximado (tokens) e completude do relatorio.
"""

from .metricas import (
    MetricasCaso,
    AgregadoModelo,
    avaliar_caso,
    agregar,
    ground_truth_do_caso,
)

__all__ = [
    "MetricasCaso",
    "AgregadoModelo",
    "avaliar_caso",
    "agregar",
    "ground_truth_do_caso",
]
