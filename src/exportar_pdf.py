"""
Ponto de entrada de linha de comando: gera o relatorio clinico de um caso e
tambem exporta o PDF, imprimindo o resultado combinado em JSON no stdout.

Reusa gerar_relatorio.gerar() para nao duplicar a chamada ao LLM. Pensado para
automacao, como alternativa a gerar_relatorio quando o destino final e um
arquivo PDF em disco.

A pergunta e OPCIONAL, como em gerar_relatorio: sem ela o modelo faz a analise
completa do caso.

Uso:
    python -m src.exportar_pdf --paciente patient_0001 \
        --modelo gemini-flash-lite --saida /tmp/relatorio.pdf
"""

import argparse
import json
import sys

from . import gerar_relatorio
from .export_pdf import relatorio_para_pdf
from .llm import catalogo
from .llm.relatorio import RelatorioClinico


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera o relatorio clinico de um caso e exporta em PDF."
    )
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
    parser.add_argument("--saida", required=True, help="Caminho do PDF de saida")
    args = parser.parse_args()

    saida = gerar_relatorio.gerar(args.paciente, args.pergunta, args.modelo)

    saida["arquivo_pdf"] = None
    if saida["ok"]:
        relatorio = RelatorioClinico.do_dict(saida["relatorio"])
        pdf_bytes = relatorio_para_pdf(
            paciente_id=saida["paciente"],
            pergunta=saida["pergunta"],
            modelo=saida["modelo"],
            relatorio=relatorio,
        )
        with open(args.saida, "wb") as f:
            f.write(pdf_bytes)
        saida["arquivo_pdf"] = args.saida

    json.dump(saida, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.exit(0 if saida["ok"] else 1)


if __name__ == "__main__":
    main()
