"""
Leitura do subconjunto ja organizado por paciente.

Esta e a fronteira que o resto da aplicacao (interface, prompts, relatorio)
enxerga: a partir daqui o formato e sempre o mesmo -- quatro arquivos por
paciente -- independentemente de a modalidade ser real ou mock. Trocar um mock
por dado real depois nao muda nenhuma assinatura deste modulo.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from PIL import Image

from . import config

ARQUIVO_INDICE = "index.csv"
ARQUIVO_CXR = "chest_xray.png"
ARQUIVO_ECG = "ecg.csv"
ARQUIVO_LABS = "laboratory.csv"
ARQUIVO_CLINICO = "clinical_data.json"


@dataclass
class Caso:
    """Um caso clinico completo: as quatro modalidades de um mesmo paciente."""

    paciente_id: str
    radiografia: Image.Image
    ecg: pd.DataFrame
    laboratorio: pd.DataFrame
    dados_clinicos: dict

    @property
    def proveniencia(self) -> dict:
        return self.dados_clinicos["_proveniencia"]

    @property
    def tem_radiografia_real(self) -> bool:
        return self.proveniencia["radiografia"] == "real"


def _raiz(base: Path | None = None) -> Path:
    base = base or config.SUBSET_DIR
    if not base.is_dir():
        raise FileNotFoundError(
            f"Subconjunto nao encontrado em {base}. "
            f"Gere-o com: python -m src.build_subset"
        )
    return base


def _pasta_paciente(paciente_id: str, base: Path | None = None) -> Path:
    pasta = _raiz(base) / paciente_id
    if not pasta.is_dir():
        raise FileNotFoundError(f"Paciente desconhecido: {paciente_id}")
    return pasta


def listar_pacientes(base: Path | None = None) -> pd.DataFrame:
    """Indice do subconjunto, com a proveniencia de cada caso."""
    return pd.read_csv(_raiz(base) / ARQUIVO_INDICE)


def carregar_radiografia(paciente_id: str, base: Path | None = None) -> Image.Image:
    return Image.open(_pasta_paciente(paciente_id, base) / ARQUIVO_CXR)


def carregar_ecg(paciente_id: str, base: Path | None = None) -> pd.DataFrame:
    """ECG de 12 derivacoes, com `tempo_s` na primeira coluna."""
    return pd.read_csv(_pasta_paciente(paciente_id, base) / ARQUIVO_ECG)


def carregar_laboratorio(paciente_id: str, base: Path | None = None) -> pd.DataFrame:
    """Os 50 exames, incluindo os ausentes (coluna `ausente`)."""
    return pd.read_csv(_pasta_paciente(paciente_id, base) / ARQUIVO_LABS)


def carregar_dados_clinicos(paciente_id: str, base: Path | None = None) -> dict:
    caminho = _pasta_paciente(paciente_id, base) / ARQUIVO_CLINICO
    return json.loads(caminho.read_text(encoding="utf-8"))


def carregar_caso(paciente_id: str, base: Path | None = None) -> Caso:
    """Carrega as quatro modalidades de um paciente de uma vez."""
    return Caso(
        paciente_id=paciente_id,
        radiografia=carregar_radiografia(paciente_id, base),
        ecg=carregar_ecg(paciente_id, base),
        laboratorio=carregar_laboratorio(paciente_id, base),
        dados_clinicos=carregar_dados_clinicos(paciente_id, base),
    )


def exames_presentes(laboratorio: pd.DataFrame) -> pd.DataFrame:
    """Filtra a tabela de laboratorio para os exames efetivamente medidos."""
    return laboratorio[~laboratorio["ausente"]].reset_index(drop=True)
