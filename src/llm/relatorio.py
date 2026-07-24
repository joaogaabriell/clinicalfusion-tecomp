"""
Esquema do relatorio clinico estruturado que o LLM deve produzir (RF08/RF09).

O relatorio tem duas partes:

1. `achados_radiologicos` -- um dicionario achado -> {positivo, negativo,
   indeterminado} sobre os 14 achados do CheXpert. E a parte AVALIAVEL: o
   benchmark compara esse campo com o ground-truth real do dataset
   (`clinical_data.json -> radiografia.achados_chexpert`). Ver src/benchmark.

2. O relatorio educacional em si -- resumo, achados principais, hipoteses,
   justificativa, exames sugeridos e aviso -- que atende ao RF09.

Manter as duas partes no mesmo esquema garante que a nota objetiva (achados) e a
resposta que o usuario le venham da MESMA inferencia, sem uma segunda chamada.
"""

import json
from dataclasses import dataclass, field

from .. import config

# Valores possiveis para cada achado CheXpert na saida do modelo.
VALOR_ACHADO = ("positivo", "negativo", "indeterminado")


@dataclass
class RelatorioClinico:
    """Relatorio estruturado devolvido pelo LLM para um caso."""

    resumo: str
    achados_radiologicos: dict[str, str]
    achados_principais: list[str] = field(default_factory=list)
    hipoteses: list[str] = field(default_factory=list)
    justificativa: str = ""
    exames_sugeridos: list[str] = field(default_factory=list)
    aviso: str = ""

    @classmethod
    def do_dict(cls, dados: dict) -> "RelatorioClinico":
        """Constroi a partir do dict retornado pelo modelo, tolerando ausencias."""
        achados = dados.get("achados_radiologicos") or {}
        # Normaliza: so mantem achados conhecidos e valores validos.
        achados_norm = {}
        for achado in config.ACHADOS_CHEXPERT:
            valor = str(achados.get(achado, "indeterminado")).strip().lower()
            achados_norm[achado] = valor if valor in VALOR_ACHADO else "indeterminado"
        return cls(
            resumo=str(dados.get("resumo", "")).strip(),
            achados_radiologicos=achados_norm,
            achados_principais=list(dados.get("achados_principais") or []),
            hipoteses=list(dados.get("hipoteses") or []),
            justificativa=str(dados.get("justificativa", "")).strip(),
            exames_sugeridos=list(dados.get("exames_sugeridos") or []),
            aviso=str(dados.get("aviso", "")).strip(),
        )

    @classmethod
    def do_json(cls, texto: str) -> "RelatorioClinico":
        """
        Constroi a partir de texto JSON, tolerando cercas de codigo (```json).

        Alguns modelos embrulham o JSON em blocos markdown mesmo quando pedimos
        JSON puro; removemos a cerca antes de parsear.
        """
        return cls.do_dict(_extrair_json(texto))

    def positivos(self) -> list[str]:
        """Achados que o modelo marcou como presentes."""
        return [a for a, v in self.achados_radiologicos.items() if v == "positivo"]


def _extrair_json(texto: str) -> dict:
    """Extrai o objeto JSON de uma resposta, removendo cercas markdown se houver."""
    limpo = texto.strip()
    if limpo.startswith("```"):
        # Remove a primeira linha (```json ou ```) e a cerca final.
        linhas = limpo.splitlines()
        linhas = linhas[1:]
        if linhas and linhas[-1].strip().startswith("```"):
            linhas = linhas[:-1]
        limpo = "\n".join(linhas).strip()
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        # Ultima tentativa: pega do primeiro { ao ultimo }.
        inicio, fim = limpo.find("{"), limpo.rfind("}")
        if inicio != -1 and fim != -1 and fim > inicio:
            return json.loads(limpo[inicio : fim + 1])
        raise


def json_schema() -> dict:
    """
    JSON Schema do relatorio, para os provedores que suportam saida estruturada.

    Todos os 14 achados sao obrigatorios para que o vetor de avaliacao seja
    sempre completo (a ausencia de um achado e informacao, como no dataset).
    """
    achado_enum = {"type": "string", "enum": list(VALOR_ACHADO)}
    return {
        "type": "object",
        "properties": {
            "resumo": {"type": "string"},
            "achados_radiologicos": {
                "type": "object",
                "properties": {a: achado_enum for a in config.ACHADOS_CHEXPERT},
                "required": list(config.ACHADOS_CHEXPERT),
                "additionalProperties": False,
            },
            "achados_principais": {"type": "array", "items": {"type": "string"}},
            "hipoteses": {"type": "array", "items": {"type": "string"}},
            "justificativa": {"type": "string"},
            "exames_sugeridos": {"type": "array", "items": {"type": "string"}},
            "aviso": {"type": "string"},
        },
        "required": [
            "resumo",
            "achados_radiologicos",
            "achados_principais",
            "hipoteses",
            "justificativa",
            "exames_sugeridos",
            "aviso",
        ],
        "additionalProperties": False,
    }
