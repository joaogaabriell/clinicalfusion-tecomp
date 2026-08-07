"""
Envio do relatorio pronto ao workflow do n8n, que arquiva o PDF localmente.

A interface ja tem o relatorio e o PDF em maos quando o usuario clica em "Gerar
relatorio". Em vez de o n8n refazer a inferencia (o que custaria uma segunda
chamada paga e poderia produzir um texto diferente do que esta na tela), o app
manda o PDF pronto em base64 e o workflow so arquiva. Ver docs/09-integracao-n8n.md.

O envio e OPCIONAL: sem a variavel `CLINICALFUSION_N8N_WEBHOOK` (ou com o n8n
fora do ar) o app funciona exatamente como antes, apenas sem arquivar. Nada aqui
pode derrubar a geracao do relatorio -- quem chama trata o ErroN8N.
"""

import base64
import json
import os
import urllib.error
import urllib.request

from . import config

# Path do no Webhook no workflow "Relatorio Clinico -> pasta sincronizada".
# /webhook/ (producao) exige o workflow ATIVO no n8n; /webhook-test/ so responde
# enquanto o botao "Test workflow" estiver escutando, e serve para depurar.
URL_PADRAO = "http://localhost:5678/webhook/relatorio-clinico"

_ENV_URL = "CLINICALFUSION_N8N_WEBHOOK"


class ErroN8N(Exception):
    """Falha ao entregar o relatorio ao n8n."""


def url_webhook() -> str | None:
    """URL configurada do webhook, ou None se a integracao estiver desligada."""
    config.carregar_env()
    valor = (os.environ.get(_ENV_URL) or "").strip()
    return valor or None


def diagnostico_visivel() -> bool:
    """
    Se a interface deve mostrar o motivo tecnico de uma falha de arquivamento.

    Para o usuario final e ruido: ele nao administra o n8n e o relatorio dele saiu
    normalmente. O motivo fica no log do container, e na tela so com
    CLINICALFUSION_DEBUG=1.
    """
    config.carregar_env()
    return (os.environ.get("CLINICALFUSION_DEBUG") or "").strip().lower() in {
        "1",
        "true",
        "sim",
    }


def enviar_relatorio(
    paciente_id: str,
    pergunta: str | None,
    modelo: str,
    pdf_bytes: bytes,
    timeout: float = 20.0,
) -> str:
    """
    Entrega o PDF ao workflow do n8n.

    `pergunta` e opcional -- a interface gera o relatorio completo sem pergunta
    digitada. A chave continua sempre no JSON (string vazia quando nao ha) para
    nao quebrar expressoes ja escritas no workflow.

    Returns:
        O nome do arquivo enviado.

    Raises:
        ErroN8N: integracao desligada, n8n fora do ar ou workflow inativo.
    """
    url = url_webhook()
    if not url:
        raise ErroN8N(
            f"Integracao desligada: defina {_ENV_URL} (ex.: {URL_PADRAO})."
        )

    nome = f"relatorio_{paciente_id}_{modelo}.pdf"
    corpo = json.dumps(
        {
            "paciente": paciente_id,
            "pergunta": (pergunta or "").strip(),
            "modelo": modelo,
            "arquivo": nome,
            "pdf_base64": base64.standard_b64encode(pdf_bytes).decode("ascii"),
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url, data=corpo, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resposta:
            resposta.read()
        return nome
    except urllib.error.HTTPError as exc:
        detalhe = ""
        try:
            detalhe = exc.read().decode("utf-8", "replace")[:200]
        except Exception:  # pragma: no cover - corpo ilegivel
            pass
        if exc.code == 404:
            # O 404 do n8n aqui quase sempre e workflow inativo, nao URL errada:
            # o path /webhook/ so existe enquanto o workflow esta ativo.
            raise ErroN8N(
                "O n8n respondeu 404. Ative o workflow "
                '"Relatório Clínico → pasta sincronizada" (chave Active, canto '
                "superior direito) -- a URL de producao so responde com ele ativo."
            ) from exc
        raise ErroN8N(f"O n8n respondeu HTTP {exc.code}. {detalhe}") from exc
    except urllib.error.URLError as exc:
        raise ErroN8N(
            f"Nao consegui falar com o n8n em {url} ({exc.reason}). "
            "Confira se o container esta no ar: docker ps."
        ) from exc
