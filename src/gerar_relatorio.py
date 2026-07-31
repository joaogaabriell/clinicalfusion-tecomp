"""
Ponto de entrada de linha de comando: gera o relatorio clinico de um caso e o
imprime em JSON no stdout.

Serve para automacao (ex.: n8n via no "Execute Command", ou um cron): recebe o
paciente e o modelo, e devolve o relatorio estruturado + telemetria.

A pergunta e OPCIONAL -- sem ela o modelo faz a analise completa do caso, que e
o mesmo fluxo da interface. Passe --pergunta so para orientar o recorte.

Uso:
    python -m src.gerar_relatorio --paciente patient_0001 --modelo gemini-flash-lite
    python -m src.gerar_relatorio --paciente patient_0001 \
        --pergunta "Quais os principais achados?"
"""

import argparse
import json
import sys
from dataclasses import asdict

from . import config, loaders
from .llm import catalogo, prompt as prompt_mod


def gerar(paciente_id: str, pergunta: str | None, chave_modelo: str) -> dict:
    """Gera o relatorio de um caso e devolve um dict serializavel."""
    config.carregar_env()
    candidato = catalogo.por_chave(chave_modelo)
    if not candidato.disponivel():
        raise SystemExit(
            f"Modelo '{chave_modelo}' indisponivel: defina {candidato.env_var}."
        )

    caso = loaders.carregar_caso(paciente_id)
    p = prompt_mod.montar_prompt(caso, pergunta)
    resposta = candidato.instanciar().gerar(p)

    saida = {
        "paciente": paciente_id,
        "pergunta": (pergunta or "").strip(),
        "modelo": resposta.modelo,
        "provedor": resposta.provedor,
        "ok": resposta.ok,
        "erro": resposta.erro,
        "latencia_s": round(resposta.latencia_s, 3),
        "tokens_entrada": resposta.tokens_entrada,
        "tokens_saida": resposta.tokens_saida,
        "custo_usd": round(
            candidato.custo_usd(resposta.tokens_entrada, resposta.tokens_saida), 6
        ),
        "relatorio": asdict(resposta.relatorio) if resposta.relatorio else None,
    }
    return saida


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o relatorio clinico de um caso.")
    parser.add_argument("--paciente", required=True, help="Ex.: patient_0001")
    parser.add_argument(
        "--pergunta",
        default=None,
        help="Opcional: orienta o recorte. Sem ela, analise completa do caso.",
    )
    parser.add_argument(
        "--modelo",
        default=catalogo.CHAVES_PADRAO[0],
        help=f"Chave do catalogo (padrao: {catalogo.CHAVES_PADRAO[0]}).",
    )
    args = parser.parse_args()

    saida = gerar(args.paciente, args.pergunta, args.modelo)
    json.dump(saida, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    # Codigo de saida != 0 quando o modelo falhou, para o orquestrador detectar.
    sys.exit(0 if saida["ok"] else 1)


if __name__ == "__main__":
    main()
