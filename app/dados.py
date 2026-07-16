"""
Ponte entre a interface e o subconjunto do Symile-MIMIC.

Traduz o que `src.loaders` entrega para o formato que a tela consome: rotulos em
portugues, tabelas prontas para exibir e as contas de apoio. Nao importa
streamlit de proposito -- assim continua testavel fora do app.

O que existe de verdade no dataset e o que nao existe:
  - ha demografia, dados da admissao, os 50 exames e os achados do CheXpert;
  - NAO ha queixa principal, historia clinica, comorbidades, medicacoes,
    alergias nem sinais vitais. O quadro precisa ser inferido das evidencias.
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, loaders  # noqa: E402

# Um percentil abaixo de 5% ou acima de 95% e um valor extremo em relacao a
# distribuicao de treino. Nao e um limite clinico: o MIMIC nao distribui as
# faixas de referencia dos exames, entao nao ha como afirmar "alterado".
LIMITE_INFERIOR = 0.05
LIMITE_SUPERIOR = 0.95

SEXO = {"M": "Masculino", "F": "Feminino"}


def subconjunto_disponivel() -> bool:
    return (config.SUBSET_DIR / loaders.ARQUIVO_INDICE).is_file()


def listar_casos() -> pd.DataFrame:
    return loaders.listar_pacientes()


AUSENTE = "—"


def texto(valor, sufixo: str = "") -> str:
    """
    Valor pronto para a tela; campo ausente vira travessao.

    O `build_subset` deixa `idade`, `sexo` e afins como None quando a coluna nao
    veio preenchida. Sem este guard, a interpolacao em f-string mostraria o
    literal "None" para quem usa o app.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return AUSENTE
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return f"{valor}{sufixo}"


def idade_texto(demografia: dict) -> str:
    return texto(demografia.get("idade"), " anos")


def rotulo_paciente(paciente_id: str, indice: pd.DataFrame) -> str:
    """Rotulo do seletor: `patient_0001 — F, 61 anos`."""
    linha = indice[indice["paciente_id"] == paciente_id].iloc[0]
    return f"{paciente_id} — {texto(linha['sexo'])}, {texto(linha['idade'], ' anos')}"


def carregar(paciente_id: str) -> loaders.Caso:
    return loaders.carregar_caso(paciente_id)


def sexo_extenso(sigla: str | None) -> str:
    return SEXO.get(sigla, sigla or AUSENTE)


def dias_internado(clinicos: dict) -> int | None:
    """Duracao da internacao, a partir das datas reais da admissao."""
    admissao = clinicos["admissao"]
    if not admissao.get("admissao_em") or not admissao.get("alta_em"):
        return None
    formato = "%Y-%m-%d %H:%M:%S"
    entrada = datetime.strptime(admissao["admissao_em"], formato)
    saida = datetime.strptime(admissao["alta_em"], formato)
    return (saida - entrada).days


def achados_positivos(clinicos: dict) -> list[str]:
    """Achados que o laudo do CheXpert marcou como presentes."""
    achados = clinicos["radiografia"]["achados_chexpert"]
    return [nome for nome, valor in achados.items() if valor == "positivo"]


def tabela_achados(clinicos: dict) -> pd.DataFrame:
    achados = clinicos["radiografia"]["achados_chexpert"]
    if not achados:
        return pd.DataFrame(columns=["Achado", "CheXpert"])
    return pd.DataFrame(
        [
            {"Achado": nome, "CheXpert": valor.capitalize()}
            for nome, valor in achados.items()
        ]
    )


def _situacao(linha: pd.Series) -> str:
    if linha["ausente"]:
        return "Não medido"
    percentil = linha["percentil"]
    if pd.isna(percentil):
        return "—"
    if percentil <= LIMITE_INFERIOR:
        return "Percentil baixo"
    if percentil >= LIMITE_SUPERIOR:
        return "Percentil alto"
    return "Faixa central"


def tabela_laboratorio(laboratorio: pd.DataFrame) -> pd.DataFrame:
    """Tabela de exames pronta para exibir, com o percentil em porcentagem."""
    tabela = laboratorio.copy()
    tabela["Situação"] = tabela.apply(_situacao, axis=1)
    tabela["Percentil"] = (tabela["percentil"] * 100).round(1)
    return tabela.rename(columns={"exame": "Exame", "valor": "Valor"})[
        ["Exame", "Valor", "Percentil", "Situação"]
    ]


def exames_extremos(tabela: pd.DataFrame) -> pd.DataFrame:
    """Exames medidos cujo valor esta nas caudas da distribuicao de treino."""
    return tabela[tabela["Situação"].isin(["Percentil baixo", "Percentil alto"])]


def derivacoes() -> list[str]:
    return config.ECG_DERIVACOES
