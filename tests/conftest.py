"""
Fixtures dos testes.

Os testes nao podem depender do Symile-MIMIC real: ele e credenciado e nem todo
integrante da equipe tem acesso. Aqui montamos um caso ficticio com o mesmo
formato das linhas do dataset.
"""

import numpy as np
import pandas as pd
import pytest

from src import build_subset, config, mock


@pytest.fixture
def caso_bruto() -> pd.Series:
    """Uma linha no formato do `test.csv`: identificadores + 50 exames."""
    valores = {"subject_id": 10000001, "hadm_id": 20000001}
    for posicao, itemid in enumerate(config.LABS):
        # Deixa os tres ultimos exames ausentes, para cobrir o caso com NaN.
        ausente = posicao >= len(config.LABS) - 3
        valores[itemid] = np.nan if ausente else 10.0 + posicao
        valores[f"{itemid}_percentile"] = np.nan if ausente else 0.5
    return pd.Series(valores)


@pytest.fixture
def caso_clinico() -> pd.Series:
    """Uma linha no formato do `symile_mimic_data.csv`."""
    valores = {
        "age": 67,
        "gender": "M",
        "race": "WHITE",
        "admission_type": "EW EMER.",
        "admission_location": "EMERGENCY ROOM",
        "discharge_location": "HOME",
        "hospital_expire_flag": 0,
        "admittime": "2150-01-01 10:00:00",
        "dischtime": "2150-01-08 14:00:00",
        "cxr_ViewPosition": "PA",
    }
    for achado in config.ACHADOS_CHEXPERT:
        valores[achado] = np.nan
    valores["Cardiomegaly"] = 1.0
    valores["Pneumonia"] = 0.0
    valores["Edema"] = -1.0
    return pd.Series(valores)


@pytest.fixture
def subconjunto(tmp_path, caso_bruto, caso_clinico):
    """Um subconjunto minimo de um paciente, no disco, pronto para ser lido."""
    build_subset._escrever_paciente(
        tmp_path,
        "patient_0001",
        caso_bruto,
        caso_clinico,
        mock.gerar_cxr_placeholder("patient_0001"),
        cxr_real=False,
    )
    pd.DataFrame(
        [{"paciente_id": "patient_0001", "cxr_real": False, "ecg_real": False}]
    ).to_csv(tmp_path / "index.csv", index=False)
    return tmp_path
