"""
Exportacao do relatorio clinico para PDF (desafio extra do enunciado).

Usa fpdf2 com a fonte core Helvetica, que cobre o latin-1 -- suficiente para o
portugues. Caracteres fora do latin-1 (travessao, bullet, setas) sao trocados
por equivalentes antes de escrever, para o PDF nunca quebrar.
"""

from .llm.relatorio import RelatorioClinico

# Substituicoes de caracteres unicode comuns que nao existem no latin-1.
_SUBSTITUICOES = {
    "—": "-",  # travessao longo
    "–": "-",  # travessao curto
    "•": "-",  # bullet
    "→": "->",  # seta
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "…": "...",
}


def _latin1(texto: str) -> str:
    """Deixa o texto seguro para a fonte core do fpdf2 (latin-1)."""
    for origem, destino in _SUBSTITUICOES.items():
        texto = texto.replace(origem, destino)
    return texto.encode("latin-1", "replace").decode("latin-1")


def relatorio_para_pdf(
    paciente_id: str,
    pergunta: str | None,
    modelo: str,
    relatorio: RelatorioClinico,
    versao_paciente: str | None = None,
) -> bytes:
    """Monta o PDF do relatorio e devolve os bytes (para st.download_button)."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    def celula(txt: str, altura: float):
        # new_x=LMARGIN/new_y=NEXT devolve o cursor a esquerda na proxima linha;
        # sem isso, multi_cell(0,...) deixa o x na margem direita e a chamada
        # seguinte falha por falta de espaco horizontal.
        pdf.multi_cell(0, altura, _latin1(txt), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def titulo(txt: str, tam: int = 13):
        pdf.set_font("Helvetica", "B", tam)
        celula(txt, 7)
        pdf.ln(1)

    def paragrafo(txt: str):
        pdf.set_font("Helvetica", "", 11)
        celula(txt, 6)
        pdf.ln(1)

    def itens(lista: list[str]):
        pdf.set_font("Helvetica", "", 11)
        for item in lista:
            celula(f"  - {item}", 6)
        pdf.ln(1)

    titulo("ClinicalFusion - Relatorio clinico estruturado", 15)
    pdf.set_font("Helvetica", "", 10)
    celula(f"Caso: {paciente_id}   |   Modelo: {modelo}", 5)
    # A interface gera o relatorio sem pergunta digitada; a linha so aparece
    # quando alguem passou uma (comparacao entre casos, CLI).
    if pergunta and pergunta.strip():
        celula(f"Pergunta: {pergunta.strip()}", 5)
    pdf.ln(3)

    titulo("1. Resumo do caso")
    paragrafo(relatorio.resumo or "-")

    titulo("2. Principais achados")
    itens(relatorio.achados_principais or ["-"])

    positivos = relatorio.positivos()
    paragrafo(
        "Achados radiologicos (CheXpert) presentes: "
        + (", ".join(positivos) if positivos else "nenhum")
    )

    titulo("3. Hipoteses clinicas (educacionais)")
    itens(relatorio.hipoteses or ["-"])

    titulo("4. Justificativa")
    paragrafo(relatorio.justificativa or "-")

    titulo("5. Exames complementares sugeridos")
    itens(relatorio.exames_sugeridos or ["-"])

    if versao_paciente:
        pdf.add_page()
        titulo("Versao em linguagem acessivel ao paciente")
        paragrafo(versao_paciente)

    titulo("Aviso", 11)
    paragrafo(
        relatorio.aviso
        or "Ferramenta educacional. Nao substitui avaliacao medica profissional."
    )

    saida = pdf.output()
    return bytes(saida)
