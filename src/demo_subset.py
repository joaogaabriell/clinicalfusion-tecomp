"""
Gera um subconjunto de DEMONSTRACAO, com casos ficticios, no mesmo formato do
subconjunto real produzido por `src.build_subset`.

O Symile-MIMIC e de acesso credenciado e sua DUA proibe redistribuicao, entao a
interface nao pode depender de receber dado real: sem ele, o app so exibia a tela
"Subconjunto nao encontrado". Este modulo produz casos inventados para que a
interface seja demonstravel por quem nao tem (nem deve receber) os dados reais.

O formato de saida e compativel com o de `build_subset` (`index.csv` + uma pasta
por paciente com as quatro modalidades): `src.loaders` le os dois sem distincao,
dispensando um caminho de codigo alternativo na interface.

Nada aqui vem do MIMIC. Os valores sao sorteados de faixas plausiveis, e a
proveniencia de cada caso declara isso -- na tela e no JSON.
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from . import config, mock

# Cada caso escreve um ECG de 5000 amostras x 12 derivacoes (~700 KB de CSV).
# 24 da variedade para navegar e mantem a geracao em poucos segundos -- ela roda
# no primeiro uso do app.
N_CASOS_PADRAO = 24

FONTE = "DEMONSTRACAO — casos ficticios, nenhum dado do Symile-MIMIC"

_SEXOS = ["M", "F"]
_RACAS = ["WHITE", "BLACK/AFRICAN AMERICAN", "HISPANIC/LATINO", "ASIAN", "OTHER"]
_TIPOS_ADMISSAO = ["EMERGENCY", "URGENT", "ELECTIVE", "OBSERVATION ADMIT"]
_ORIGENS = ["EMERGENCY ROOM", "PHYSICIAN REFERRAL", "TRANSFER FROM HOSPITAL"]
_DESFECHOS = ["HOME", "HOME HEALTH CARE", "REHAB", "SKILLED NURSING FACILITY"]
_POSICOES_CXR = ["PA", "AP", "LATERAL"]
_ROTULOS_CHEXPERT = ["positivo", "negativo", "incerto"]

# Faixas de sorteio, nao faixas de referencia clinica: servem so para a tela ter
# numeros plausiveis. O app nunca afirma "alterado" (ver app/dados.py).
_FAIXA_GENERICA = (0.5, 200.0)

_FAIXAS = {
    "Hematocrit": (28.0, 48.0),
    "Hemoglobin": (9.0, 16.5),
    "Platelet Count": (120.0, 420.0),
    "White Blood Cells": (3.5, 18.0),
    "Creatinine": (0.5, 3.2),
    "Potassium": (3.0, 5.6),
    "Sodium": (130.0, 148.0),
    "Chloride": (95.0, 112.0),
    "Bicarbonate": (18.0, 30.0),
    "Urea Nitrogen": (8.0, 60.0),
    "Glucose": (70.0, 280.0),
    "Anion Gap": (6.0, 20.0),
    "Magnesium": (1.4, 2.6),
    "Calcium, Total": (7.5, 10.5),
    "Phosphate": (2.0, 5.5),
}


def _destino(destino: Path | None) -> Path:
    """
    Pasta de saida padrao, resolvida a cada chamada.

    Nao fixada numa constante de modulo para acompanhar `config.DEMO_DIR`, que
    depende do ambiente e e trocado nos testes.
    """
    return destino or config.DEMO_DIR


def _rng(paciente_id: str) -> np.random.Generator:
    """
    Gerador deterministico por paciente: o mesmo `paciente_id` devolve o mesmo
    caso em qualquer maquina. Sem isso, uma captura de tela do relatorio nao
    corresponderia a proxima execucao.
    """
    semente = int.from_bytes(paciente_id.encode("utf-8"), "big") % (2**32)
    return np.random.default_rng(semente)


def _tabela_laboratorio(rng: np.random.Generator) -> pd.DataFrame:
    """
    Monta o laboratory.csv ficticio, com os mesmos 50 exames em ordem fixa.

    Parte dos exames fica sem valor, como no subconjunto real: a ausencia de
    exame e um dado da tela, nao uma falha.
    """
    linhas = []
    for itemid, nome in config.LABS.items():
        # ~30%, a mesma ordem de grandeza do subset real.
        ausente = bool(rng.random() < 0.30)
        if ausente:
            valor = percentil = None
        else:
            baixo, alto = _FAIXAS.get(nome, _FAIXA_GENERICA)
            valor = round(float(rng.uniform(baixo, alto)), 2)
            percentil = round(float(rng.random()), 6)
        linhas.append(
            {
                "itemid": itemid,
                "exame": nome,
                "valor": valor,
                "percentil": percentil,
                "ausente": ausente,
            }
        )
    return pd.DataFrame(linhas)


def _tabela_ecg(paciente_id: str) -> pd.DataFrame:
    """ECG ficticio no contrato real: `tempo_s` + as 12 derivacoes."""
    sinal = mock.gerar_ecg(paciente_id)
    tempo = np.arange(config.ECG_N_AMOSTRAS) / config.ECG_FREQUENCIA_HZ
    tabela = pd.DataFrame(sinal, columns=config.ECG_DERIVACOES)
    tabela.insert(0, "tempo_s", tempo)
    return tabela


def _achados_chexpert(rng: np.random.Generator) -> dict[str, str]:
    """Alguns achados sorteados; os nao mencionados ficam fora, como no real."""
    achados = {}
    for achado in config.ACHADOS_CHEXPERT:
        if rng.random() < 0.45:  # nem todo achado aparece no laudo
            continue
        achados[achado] = str(rng.choice(_ROTULOS_CHEXPERT))
    return achados


def _dados_clinicos(paciente_id: str, rng: np.random.Generator) -> dict:
    """Monta o clinical_data.json ficticio, com a proveniencia bem marcada."""
    dia = int(rng.integers(1, 29))
    mes = int(rng.integers(1, 13))
    return {
        "paciente_id": paciente_id,
        # Faixa 9xxxxxxx, fora da usada pelo MIMIC: um id ficticio nunca pode ser
        # confundido com (ou cruzado contra) um paciente real.
        "subject_id": 90000000 + int(rng.integers(0, 9999999)),
        "hadm_id": 90000000 + int(rng.integers(0, 9999999)),
        "demografia": {
            "idade": int(rng.integers(24, 89)),
            "sexo": str(rng.choice(_SEXOS)),
            "raca": str(rng.choice(_RACAS)),
        },
        "admissao": {
            "tipo": str(rng.choice(_TIPOS_ADMISSAO)),
            "origem": str(rng.choice(_ORIGENS)),
            "desfecho": str(rng.choice(_DESFECHOS)),
            "obito_hospitalar": False,
            "admissao_em": f"2180-{mes:02d}-{dia:02d} 08:00:00",
            "alta_em": f"2180-{mes:02d}-{min(dia + 4, 28):02d} 16:00:00",
        },
        "radiografia": {
            "posicao": str(rng.choice(_POSICOES_CXR)),
            "achados_chexpert": _achados_chexpert(rng),
        },
        "_proveniencia": {
            "aviso": (
                "MODO DEMONSTRACAO. Caso ficticio, gerado por src/demo_subset.py. "
                "Uso exclusivamente educacional. Nao substitui avaliacao medica."
            ),
            "fonte": FONTE,
            "dados_clinicos": "mock",
            "laboratorio": "mock",
            "radiografia": "mock",
            "ecg": "mock",
            "motivo_mock": (
                "Subconjunto de demonstracao: o Symile-MIMIC e de acesso "
                "credenciado e sua DUA proibe redistribuicao, entao nenhum dado "
                "real acompanha o app. Para usar os dados reais, gere o "
                "subconjunto na sua maquina com `python -m src.build_subset`."
            ),
        },
    }


def _escrever_paciente(destino: Path, paciente_id: str) -> dict:
    """Escreve as quatro modalidades de um caso ficticio e devolve a linha do indice."""
    rng = _rng(paciente_id)
    pasta = destino / paciente_id
    pasta.mkdir(parents=True, exist_ok=True)

    laboratorio = _tabela_laboratorio(rng)
    clinicos = _dados_clinicos(paciente_id, rng)

    # Placeholder deliberado -- um cartao de aviso legivel, nao uma imagem
    # parecida com radiografia (mesma decisao de src/mock.py).
    imagem: Image.Image = mock.gerar_cxr_placeholder(paciente_id)
    imagem.save(pasta / "chest_xray.png")
    _tabela_ecg(paciente_id).to_csv(pasta / "ecg.csv", index=False, float_format="%.4f")
    laboratorio.to_csv(pasta / "laboratory.csv", index=False)
    (pasta / "clinical_data.json").write_text(
        json.dumps(clinicos, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "paciente_id": paciente_id,
        "subject_id": clinicos["subject_id"],
        "hadm_id": clinicos["hadm_id"],
        "idade": clinicos["demografia"]["idade"],
        "sexo": clinicos["demografia"]["sexo"],
        "cxr_real": False,
        "ecg_real": False,
        "labs_presentes": int((~laboratorio["ausente"]).sum()),
    }


def construir(
    n_casos: int = N_CASOS_PADRAO,
    destino: Path | None = None,
    limpar: bool = False,
) -> pd.DataFrame:
    """
    Gera o subconjunto de demonstracao e devolve o indice dos casos criados.

    Raises:
        ValueError: `n_casos` menor que 1.
    """
    if n_casos < 1:
        raise ValueError(f"n_casos deve ser >= 1; recebido: {n_casos}")

    destino = _destino(destino)
    if limpar and destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True, exist_ok=True)

    indice = [
        _escrever_paciente(destino, f"demo_{posicao + 1:04d}")
        for posicao in range(n_casos)
    ]
    tabela = pd.DataFrame(indice)
    tabela.to_csv(destino / "index.csv", index=False)
    return tabela


def disponivel(destino: Path | None = None) -> bool:
    """Se o subconjunto de demonstracao ja foi gerado."""
    destino = _destino(destino)
    return (destino / "index.csv").is_file()


def garantir(n_casos: int = N_CASOS_PADRAO, destino: Path | None = None) -> Path:
    """
    Devolve a pasta da demonstracao, gerando-a se ainda nao existir.

    Usado pela interface no primeiro uso: abrir o app nao deve exigir comando.
    """
    destino = _destino(destino)
    if not disponivel(destino):
        construir(n_casos, destino)
    return destino


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Gera um subconjunto de demonstracao com casos ficticios."
    )
    parser.add_argument("--n-casos", type=int, default=N_CASOS_PADRAO)
    parser.add_argument("--destino", type=Path, default=None)
    parser.add_argument(
        "--limpar", action="store_true", help="apaga a pasta antes de gerar"
    )
    args = parser.parse_args()

    tabela = construir(args.n_casos, args.destino, args.limpar)
    print(f"{len(tabela)} casos ficticios gerados em {_destino(args.destino)}")


if __name__ == "__main__":
    main()
