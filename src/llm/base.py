"""
Interface comum dos clientes de LLM multimodal.

Todo provedor (OpenAI, Google, Anthropic) implementa `ClienteLLM.gerar`, que
recebe um `PromptMultimodal` e devolve uma `RespostaLLM` com o relatorio ja
parseado e a telemetria (tokens, latencia) que o benchmark usa para comparar
custo e velocidade. Nenhuma chave de API e lida aqui: cada cliente resolve a sua
propria variavel de ambiente na hora de instanciar.
"""

import base64
import io
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from PIL import Image

from .prompt import PromptMultimodal
from .relatorio import RelatorioClinico


class ErroLLM(Exception):
    """Falha ao chamar o provedor ou ao interpretar a resposta."""


# Marcadores de erro transitorio (sobrecarga/limite momentaneo do provedor), que
# vale a pena repetir.
_MARCADORES_TRANSITORIOS = (
    "503",
    "unavailable",
    "overloaded",
    "high demand",
    "resource_exhausted",
    "rate limit",
    "429 rate",
    "temporarily",
    "timeout",
)

# Marcadores de falha permanente para a sessao (cota diaria/creditos esgotados):
# repetir so faz o app travar por minutos sem chance de sucesso.
_MARCADORES_PERMANENTES = (
    "insufficient_quota",
    "insufficient quota",
    "exceeded your current quota",
    "check your plan",
    "billing",
)


def _e_transitorio(exc: Exception) -> bool:
    msg = str(exc).lower()
    if any(marca in msg for marca in _MARCADORES_PERMANENTES):
        return False
    return any(marca in msg for marca in _MARCADORES_TRANSITORIOS)


def com_retry(fn, tentativas: int = 4, base_espera: float = 1.5):
    """
    Executa fn com algumas tentativas em caso de erro transitorio do provedor.

    Erros permanentes (credencial invalida, cota esgotada) sobem na primeira vez.
    """
    ultimo = None
    for tentativa in range(tentativas):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - reclassificado por _e_transitorio
            ultimo = exc
            if not _e_transitorio(exc) or tentativa == tentativas - 1:
                raise
            time.sleep(base_espera * (2**tentativa))
    raise ultimo  # pragma: no cover


@dataclass
class RespostaLLM:
    """Resultado de uma chamada, com relatorio parseado e telemetria."""

    modelo: str
    provedor: str
    relatorio: RelatorioClinico | None
    texto_bruto: str
    latencia_s: float
    tokens_entrada: int | None = None
    tokens_saida: int | None = None
    erro: str | None = None
    metadados: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.erro is None and self.relatorio is not None


class ClienteLLM(ABC):
    """Cliente de um provedor. Instanciar exige a chave de API do provedor."""

    provedor: str = "desconhecido"

    def __init__(self, modelo: str):
        self.modelo = modelo

    @abstractmethod
    def gerar(self, prompt: PromptMultimodal, max_tokens: int = 2000) -> RespostaLLM:
        """Envia o prompt multimodal e devolve o relatorio estruturado."""

    # -- utilitarios compartilhados ----------------------------------------

    @staticmethod
    def imagem_para_base64(imagem: Image.Image) -> str:
        """Codifica a radiografia como PNG base64 (formato aceito por todos)."""
        buffer = io.BytesIO()
        imagem.convert("RGB").save(buffer, format="PNG")
        return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")

    def _finalizar(
        self,
        texto: str,
        inicio: float,
        tokens_entrada: int | None = None,
        tokens_saida: int | None = None,
    ) -> RespostaLLM:
        """Parseia o JSON do modelo em RelatorioClinico e monta a RespostaLLM."""
        latencia = time.perf_counter() - inicio
        try:
            rel = RelatorioClinico.do_json(texto)
            return RespostaLLM(
                modelo=self.modelo,
                provedor=self.provedor,
                relatorio=rel,
                texto_bruto=texto,
                latencia_s=latencia,
                tokens_entrada=tokens_entrada,
                tokens_saida=tokens_saida,
            )
        except Exception as exc:  # JSON invalido: registra sem derrubar o benchmark
            return RespostaLLM(
                modelo=self.modelo,
                provedor=self.provedor,
                relatorio=None,
                texto_bruto=texto,
                latencia_s=latencia,
                tokens_entrada=tokens_entrada,
                tokens_saida=tokens_saida,
                erro=f"resposta nao-JSON: {exc}",
            )
