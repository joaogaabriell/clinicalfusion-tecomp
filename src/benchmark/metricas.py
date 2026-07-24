"""
Metricas do benchmark, ancoradas no ground-truth CheXpert.

O dataset traz, para cada caso com radiografia real, um subconjunto dos 14
achados do CheXpert rotulado como 'positivo' ou 'negativo'
(clinical_data.json -> radiografia.achados_chexpert). Esse e o ground-truth.

Para cada modelo comparamos o campo achados_radiologicos do relatorio com esse
rotulo, apenas nos achados que o dataset de fato rotulou. Sobre esses pares
(caso, achado) calculamos precisao/recall/F1 (classe 'positivo' = achado
presente) e acuracia. Alem disso registramos latencia, tokens e completude do
relatorio textual, para a decisao considerar tambem custo e velocidade.
"""

from dataclasses import dataclass, field

from ..llm.base import RespostaLLM
from ..llm.relatorio import RelatorioClinico


def ground_truth_do_caso(dados_clinicos: dict) -> dict[str, str]:
    """
    Extrai os achados CheXpert rotulados de um caso.

    Returns:
        dict achado -> 'positivo'|'negativo', apenas os achados presentes no
        dataset (pode ser um subconjunto dos 14).
    """
    radiografia = dados_clinicos.get("radiografia") or {}
    achados = radiografia.get("achados_chexpert") or {}
    return {
        achado: str(valor).strip().lower()
        for achado, valor in achados.items()
        if str(valor).strip().lower() in ("positivo", "negativo")
    }


@dataclass
class MetricasCaso:
    """Resultado da avaliacao de um modelo em um caso."""

    verdadeiros_positivos: int = 0
    falsos_positivos: int = 0
    falsos_negativos: int = 0
    verdadeiros_negativos: int = 0
    achados_avaliados: int = 0
    acertos: int = 0
    completude: float = 0.0
    latencia_s: float = 0.0
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_usd: float = 0.0
    falhou: bool = False


def _completude(relatorio: RelatorioClinico) -> float:
    """Fracao dos campos textuais do relatorio efetivamente preenchidos (RF09)."""
    checagens = [
        bool(relatorio.resumo),
        bool(relatorio.achados_principais),
        bool(relatorio.hipoteses),
        bool(relatorio.justificativa),
        bool(relatorio.exames_sugeridos),
        bool(relatorio.aviso),
    ]
    return sum(checagens) / len(checagens)


def avaliar_caso(resposta: RespostaLLM, ground_truth: dict[str, str]) -> MetricasCaso:
    """Compara a resposta de um modelo com o ground-truth CheXpert de um caso."""
    m = MetricasCaso(
        latencia_s=resposta.latencia_s,
        tokens_entrada=resposta.tokens_entrada or 0,
        tokens_saida=resposta.tokens_saida or 0,
    )
    if not resposta.ok or resposta.relatorio is None:
        m.falhou = True
        return m

    m.completude = _completude(resposta.relatorio)
    previsto = resposta.relatorio.achados_radiologicos
    for achado, verdadeiro in ground_truth.items():
        estimado = previsto.get(achado, "indeterminado")
        m.achados_avaliados += 1
        if estimado == verdadeiro:
            m.acertos += 1
        # Matriz de confusao para a classe "positivo" (achado presente).
        if verdadeiro == "positivo" and estimado == "positivo":
            m.verdadeiros_positivos += 1
        elif verdadeiro == "negativo" and estimado == "positivo":
            m.falsos_positivos += 1
        elif verdadeiro == "positivo" and estimado != "positivo":
            m.falsos_negativos += 1
        elif verdadeiro == "negativo" and estimado != "positivo":
            m.verdadeiros_negativos += 1
    return m


@dataclass
class AgregadoModelo:
    """Metricas agregadas de um modelo sobre todos os casos avaliados."""

    chave: str
    provedor: str
    modelo: str
    n_casos: int = 0
    n_falhas: int = 0
    vp: int = 0
    fp: int = 0
    fn: int = 0
    vn: int = 0
    achados_avaliados: int = 0
    acertos: int = 0
    soma_completude: float = 0.0
    soma_latencia: float = 0.0
    soma_tokens_entrada: int = 0
    soma_tokens_saida: int = 0
    soma_custo: float = 0.0
    casos: list[MetricasCaso] = field(default_factory=list)

    def adicionar(self, m: MetricasCaso) -> None:
        self.n_casos += 1
        if m.falhou:
            self.n_falhas += 1
        self.vp += m.verdadeiros_positivos
        self.fp += m.falsos_positivos
        self.fn += m.falsos_negativos
        self.vn += m.verdadeiros_negativos
        self.achados_avaliados += m.achados_avaliados
        self.acertos += m.acertos
        self.soma_completude += m.completude
        self.soma_latencia += m.latencia_s
        self.soma_tokens_entrada += m.tokens_entrada
        self.soma_tokens_saida += m.tokens_saida
        self.soma_custo += m.custo_usd
        self.casos.append(m)

    @property
    def precisao(self) -> float:
        denom = self.vp + self.fp
        return self.vp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.vp + self.fn
        return self.vp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precisao, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def acuracia(self) -> float:
        return self.acertos / self.achados_avaliados if self.achados_avaliados else 0.0

    @property
    def completude_media(self) -> float:
        return self.soma_completude / self.n_casos if self.n_casos else 0.0

    @property
    def latencia_media(self) -> float:
        return self.soma_latencia / self.n_casos if self.n_casos else 0.0

    @property
    def custo_medio(self) -> float:
        return self.soma_custo / self.n_casos if self.n_casos else 0.0

    def resumo(self) -> dict:
        """Dict achatado para exportar em tabela (CSV/markdown)."""
        return {
            "chave": self.chave,
            "provedor": self.provedor,
            "modelo": self.modelo,
            "n_casos": self.n_casos,
            "n_falhas": self.n_falhas,
            "f1": round(self.f1, 4),
            "precisao": round(self.precisao, 4),
            "recall": round(self.recall, 4),
            "acuracia": round(self.acuracia, 4),
            "completude": round(self.completude_media, 4),
            "latencia_media_s": round(self.latencia_media, 3),
            "tokens_entrada": self.soma_tokens_entrada,
            "tokens_saida": self.soma_tokens_saida,
            "custo_total_usd": round(self.soma_custo, 6),
            "custo_medio_usd": round(self.custo_medio, 6),
        }


def agregar(
    chave: str, provedor: str, modelo: str, metricas: list[MetricasCaso]
) -> AgregadoModelo:
    """Agrega as metricas por-caso de um modelo em um AgregadoModelo."""
    agregado = AgregadoModelo(chave=chave, provedor=provedor, modelo=modelo)
    for m in metricas:
        agregado.adicionar(m)
    return agregado
