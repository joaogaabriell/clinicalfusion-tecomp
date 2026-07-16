"""
Monta o subconjunto do ClinicalFusion no formato uma-pasta-por-paciente.

Combina o que recebemos de real (exames laboratoriais, dados demograficos e
clinicos, achados do CheXpert e as radiografias que sobreviveram no tensor
truncado) com o que precisou ser mockado (o ECG, e as radiografias ausentes).

Uso:
    python -m src.build_subset --n-casos 150

Saida (ignorada pelo Git, conforme a DUA do PhysioNet):
    data/symile-mimic/
    ├── index.csv
    ├── patient_0001/
    │   ├── chest_xray.png
    │   ├── ecg.csv
    │   ├── laboratory.csv
    │   └── clinical_data.json
    └── ...
"""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from . import config, mock, symile_source

# Rotulos do CheXpert. NaN significa que o achado nao foi mencionado no laudo.
_ROTULO_CHEXPERT = {1.0: "positivo", 0.0: "negativo", -1.0: "incerto"}


def _conferir_colunas_de_exame(casos: pd.DataFrame) -> None:
    """
    Garante que os 50 exames de `config.LABS` existem no CSV.

    Sem esta checagem, uma coluna com nome diferente do esperado passaria por
    `Series.get()` como None e o exame seria marcado como "nao medido" em todos
    os pacientes -- um erro de schema disfarcado de dado clinico ausente.
    """
    esperadas = {*config.LABS, *(f"{itemid}_percentile" for itemid in config.LABS)}
    faltando = esperadas - set(casos.columns)
    if faltando:
        raise ValueError(
            f"{len(faltando)} colunas de exame nao existem no test.csv "
            f"(ex.: {sorted(faltando)[:3]}); config.LABS esta fora de sincronia "
            f"com o dataset."
        )


def _tabela_laboratorio(caso: pd.Series) -> pd.DataFrame:
    """
    Monta o laboratory.csv de um caso a partir dos valores reais.

    Mantem os 50 exames sempre nas mesmas linhas, inclusive os ausentes, para
    que todos os pacientes tenham a mesma tabela e a ausencia seja um dado
    explicito -- e nao uma linha que sumiu.
    """
    linhas = []
    for itemid, nome in config.LABS.items():
        valor = caso.get(itemid)
        percentil = caso.get(f"{itemid}_percentile")
        ausente = pd.isna(valor)
        linhas.append(
            {
                "itemid": itemid,
                "exame": nome,
                "valor": None if ausente else float(valor),
                "percentil": None if pd.isna(percentil) else round(float(percentil), 6),
                "ausente": bool(ausente),
            }
        )
    return pd.DataFrame(linhas)


def _tabela_ecg(paciente_id: str) -> pd.DataFrame:
    """Monta o ecg.csv (mock) com o eixo de tempo e as 12 derivacoes."""
    sinal = mock.gerar_ecg(paciente_id)
    tempo = np.arange(config.ECG_N_AMOSTRAS) / config.ECG_FREQUENCIA_HZ
    tabela = pd.DataFrame(sinal, columns=config.ECG_DERIVACOES)
    tabela.insert(0, "tempo_s", tempo)
    return tabela


def _achados_chexpert(clinico: pd.Series) -> dict[str, str]:
    """Achados radiologicos reais, omitindo os nao mencionados no laudo."""
    achados = {}
    for achado in config.ACHADOS_CHEXPERT:
        valor = clinico.get(achado)
        if pd.isna(valor):
            continue
        achados[achado] = _ROTULO_CHEXPERT.get(float(valor), "desconhecido")
    return achados


def _dados_clinicos(
    paciente_id: str, caso: pd.Series, clinico: pd.Series, cxr_real: bool
) -> dict:
    """Monta o clinical_data.json, com a proveniencia de cada modalidade."""

    def campo(nome):
        valor = clinico.get(nome)
        return None if pd.isna(valor) else valor

    return {
        "paciente_id": paciente_id,
        "subject_id": int(caso["subject_id"]),
        "hadm_id": int(caso["hadm_id"]),
        "demografia": {
            "idade": int(campo("age")) if campo("age") is not None else None,
            "sexo": campo("gender"),
            "raca": campo("race"),
        },
        "admissao": {
            "tipo": campo("admission_type"),
            "origem": campo("admission_location"),
            "desfecho": campo("discharge_location"),
            "obito_hospitalar": bool(int(campo("hospital_expire_flag") or 0)),
            "admissao_em": campo("admittime"),
            "alta_em": campo("dischtime"),
        },
        "radiografia": {
            "posicao": campo("cxr_ViewPosition"),
            "achados_chexpert": _achados_chexpert(clinico),
        },
        "_proveniencia": {
            "aviso": "Uso exclusivamente educacional. Nao substitui avaliacao medica.",
            "fonte": "Symile-MIMIC 1.0.0 (PhysioNet, acesso credenciado)",
            "dados_clinicos": "real",
            "laboratorio": "real",
            "radiografia": "real" if cxr_real else "mock",
            "ecg": "mock",
            "motivo_mock": (
                "O material disponibilizado nao inclui os sinais de ECG "
                "(ecg_*.npy ausentes) e traz o cxr_test.npy truncado, com "
                "apenas as primeiras radiografias intactas."
            ),
        },
    }


def _escrever_paciente(
    destino: Path,
    paciente_id: str,
    caso: pd.Series,
    clinico: pd.Series,
    imagem: Image.Image,
    cxr_real: bool,
) -> dict:
    """Escreve as quatro modalidades de um paciente e devolve a linha do indice."""
    pasta = destino / paciente_id
    pasta.mkdir(parents=True, exist_ok=True)

    laboratorio = _tabela_laboratorio(caso)

    imagem.save(pasta / "chest_xray.png")
    _tabela_ecg(paciente_id).to_csv(pasta / "ecg.csv", index=False, float_format="%.4f")
    laboratorio.to_csv(pasta / "laboratory.csv", index=False)

    clinicos = _dados_clinicos(paciente_id, caso, clinico, cxr_real)
    (pasta / "clinical_data.json").write_text(
        json.dumps(clinicos, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "paciente_id": paciente_id,
        "subject_id": clinicos["subject_id"],
        "hadm_id": clinicos["hadm_id"],
        "idade": clinicos["demografia"]["idade"],
        "sexo": clinicos["demografia"]["sexo"],
        "cxr_real": cxr_real,
        "ecg_real": False,
        "labs_presentes": int((~laboratorio["ausente"]).sum()),
    }


def construir(
    n_casos: int = config.N_CASOS_PADRAO,
    destino: Path | None = None,
    limpar: bool = False,
) -> pd.DataFrame:
    """
    Constroi o subconjunto e devolve o indice dos pacientes gerados.

    As radiografias reais existem apenas para os primeiros casos, porque a ordem
    das linhas dos positivos do `test.csv` acompanha a ordem das imagens no
    `cxr_test.npy`. Os casos seguintes recebem placeholder.
    """
    if not config.N_CASOS_MIN <= n_casos <= config.N_CASOS_MAX:
        raise ValueError(
            f"O enunciado pede entre {config.N_CASOS_MIN} e {config.N_CASOS_MAX} "
            f"casos; recebido: {n_casos}"
        )

    destino = destino or config.SUBSET_DIR
    if limpar and destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True, exist_ok=True)

    positivos = symile_source.casos_positivos_do_test()
    if n_casos > len(positivos):
        raise ValueError(
            f"Ha apenas {len(positivos)} casos positivos disponiveis no test.csv"
        )
    _conferir_colunas_de_exame(positivos)

    clinicos = symile_source.dados_clinicos_por_admissao()
    imagens, n_declarado = symile_source.cxrs_recuperaveis()
    n_reais = len(imagens)
    print(
        f"Radiografias reais recuperadas: {n_reais} de {n_declarado} declaradas "
        f"no cxr_test.npy (arquivo truncado)."
    )

    indice = []
    for posicao in range(n_casos):
        caso = positivos.iloc[posicao]
        paciente_id = f"patient_{posicao + 1:04d}"

        cxr_real = posicao < n_reais
        if cxr_real:
            imagem = Image.fromarray(symile_source.cxr_para_uint8(imagens[posicao]))
        else:
            imagem = mock.gerar_cxr_placeholder(paciente_id)

        indice.append(
            _escrever_paciente(
                destino,
                paciente_id,
                caso,
                clinicos.loc[caso["hadm_id"]],
                imagem,
                cxr_real,
            )
        )

    tabela = pd.DataFrame(indice)
    tabela.to_csv(destino / "index.csv", index=False)
    return tabela


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--n-casos",
        type=int,
        default=config.N_CASOS_PADRAO,
        help=f"Casos a gerar (padrao: {config.N_CASOS_PADRAO})",
    )
    parser.add_argument(
        "--limpar",
        action="store_true",
        help="Apaga o subconjunto anterior antes de gerar",
    )
    argumentos = parser.parse_args()

    tabela = construir(n_casos=argumentos.n_casos, limpar=argumentos.limpar)
    reais = int(tabela["cxr_real"].sum())
    print(f"\n{len(tabela)} casos gerados em {config.SUBSET_DIR}")
    print(f"  radiografia real: {reais} | placeholder: {len(tabela) - reais}")
    print(f"  ECG: 0 reais | {len(tabela)} mock")
    print(
        f"  labs presentes por caso (mediana): {tabela['labs_presentes'].median():.0f} de 50"
    )


if __name__ == "__main__":
    main()
