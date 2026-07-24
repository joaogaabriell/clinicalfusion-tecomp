"""
Funcionalidades extras sobre o relatorio ja gerado.

Por enquanto: tradução do relatorio clinico para linguagem acessivel ao paciente
(um dos desafios extra do enunciado). Reaproveita o mesmo modelo do relatorio,
mas em uma chamada apenas-texto (a imagem ja foi interpretada na primeira etapa).
"""

from .relatorio import RelatorioClinico

_SYSTEM_PACIENTE = (
    "Voce reescreve relatorios clinicos em portugues do Brasil, em linguagem "
    "SIMPLES e acolhedora, para o proprio paciente entender -- sem jargao medico, "
    "sem numeros de exame, sem diagnostico. Explique em poucos paragrafos o que "
    "foi observado e o que pode ser conversado com o medico. Termine lembrando, "
    "com gentileza, que este texto e educativo e NAO substitui a consulta medica."
)


def _relatorio_em_texto(rel: RelatorioClinico) -> str:
    """Serializa o relatorio estruturado em texto para servir de entrada."""
    partes = [f"Resumo: {rel.resumo}"]
    if rel.achados_principais:
        partes.append("Principais achados: " + "; ".join(rel.achados_principais))
    if rel.hipoteses:
        partes.append("Hipoteses (educacionais): " + "; ".join(rel.hipoteses))
    if rel.justificativa:
        partes.append("Justificativa: " + rel.justificativa)
    if rel.exames_sugeridos:
        partes.append("Exames sugeridos: " + "; ".join(rel.exames_sugeridos))
    return "\n".join(partes)


def explicar_para_paciente(candidato, relatorio: RelatorioClinico) -> str:
    """
    Gera uma versao do relatorio em linguagem acessivel ao paciente.

    Args:
        candidato: ModeloCandidato (o mesmo usado no relatorio, idealmente).
        relatorio: RelatorioClinico ja produzido pelo LLM.

    Returns:
        Texto em linguagem simples. Em caso de falha, uma mensagem de erro.
    """
    cliente = candidato.instanciar()
    if not hasattr(cliente, "conversar"):
        raise TypeError("O cliente nao suporta chamada apenas-texto.")
    entrada = (
        "Reescreva o relatorio abaixo em linguagem simples para o paciente:\n\n"
        + _relatorio_em_texto(relatorio)
    )
    return cliente.conversar(_SYSTEM_PACIENTE, entrada)
