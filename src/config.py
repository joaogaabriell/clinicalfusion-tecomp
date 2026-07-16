"""
Configuracao central do ClinicalFusion: caminhos, specs das modalidades e
metadados publicos do MIMIC-IV.

O diretorio com o Symile-MIMIC bruto e credenciado e NAO faz parte do
repositorio. Aponte para ele com a variavel de ambiente SYMILE_MIMIC_DIR
(ver .env.example).
"""

from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

# Subconjunto gerado a partir dos dados credenciados. Ignorado pelo Git (DUA).
SUBSET_DIR = DATA_DIR / "symile-mimic"

ENV_VAR_FONTE = "SYMILE_MIMIC_DIR"

# --- Specs das modalidades -------------------------------------------------

# ECG: derivado de process_and_save_tensors.py, que empilha tensores
# (n, 1, 5000, 12) -> 12 derivacoes x 5000 amostras, normalizadas em [-1, 1].
# 5000 amostras / 10 s = 500 Hz, o padrao do MIMIC-IV-ECG.
ECG_FREQUENCIA_HZ = 500
ECG_DURACAO_S = 10
ECG_N_AMOSTRAS = ECG_FREQUENCIA_HZ * ECG_DURACAO_S
ECG_DERIVACOES = [
    "I",
    "II",
    "III",
    "aVR",
    "aVL",
    "aVF",
    "V1",
    "V2",
    "V3",
    "V4",
    "V5",
    "V6",
]

# CXR: cada imagem foi reescalada para 320 e normalizada com as estatisticas
# da ImageNet, seguindo o CheXpert.
CXR_LADO = 320
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Numero de imagens intactas no cxr_test.npy truncado que recebemos.
# Calculado em tempo de execucao por symile_source.cxrs_recuperaveis().

# Faixa de casos exigida pelo enunciado do projeto.
N_CASOS_MIN = 100
N_CASOS_MAX = 500
N_CASOS_PADRAO = 150

# --- Metadados publicos do MIMIC-IV ----------------------------------------

# itemid -> nome do exame, para os 50 exames laboratoriais mais frequentes.
# Metadado publico do MIMIC-IV (tabela d_labitems), nao contem dado de paciente.
LABS = {
    "51221": "Hematocrit",
    "51265": "Platelet Count",
    "50912": "Creatinine",
    "50971": "Potassium",
    "51222": "Hemoglobin",
    "51301": "White Blood Cells",
    "51249": "MCHC",
    "51279": "Red Blood Cells",
    "51250": "MCV",
    "51248": "MCH",
    "51277": "RDW",
    "51006": "Urea Nitrogen",
    "50983": "Sodium",
    "50902": "Chloride",
    "50882": "Bicarbonate",
    "50868": "Anion Gap",
    "50931": "Glucose",
    "50960": "Magnesium",
    "50893": "Calcium, Total",
    "50970": "Phosphate",
    "51237": "INR(PT)",
    "51274": "PT",
    "51275": "PTT",
    "51146": "Basophils",
    "51256": "Neutrophils",
    "51254": "Monocytes",
    "51200": "Eosinophils",
    "51244": "Lymphocytes",
    "52172": "RDW-SD",
    "50934": "H",
    "51678": "L",
    "50947": "I",
    "50861": "Alanine Aminotransferase (ALT)",
    "50878": "Asparate Aminotransferase (AST)",
    "50813": "Lactate",
    "50863": "Alkaline Phosphatase",
    "50885": "Bilirubin, Total",
    "50820": "pH",
    "50862": "Albumin",
    "50802": "Base Excess",
    "50821": "pO2",
    "50804": "Calculated Total CO2",
    "50818": "pCO2",
    "52075": "Absolute Neutrophil Count",
    "52073": "Absolute Eosinophil Count",
    "52074": "Absolute Monocyte Count",
    "52069": "Absolute Basophil Count",
    "51133": "Absolute Lymphocyte Count",
    "50910": "Creatine Kinase (CK)",
    "52135": "Immature Granulocytes",
}

# Os 14 achados radiologicos rotulados pelo CheXpert no MIMIC-CXR.
ACHADOS_CHEXPERT = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Enlarged Cardiomediastinum",
    "Fracture",
    "Lung Lesion",
    "Lung Opacity",
    "No Finding",
    "Pleural Effusion",
    "Pleural Other",
    "Pneumonia",
    "Pneumothorax",
    "Support Devices",
]


def _ler_dotenv(caminho: Path) -> dict[str, str]:
    """Le um .env simples (CHAVE=valor) sem depender de bibliotecas externas."""
    if not caminho.is_file():
        return {}
    valores = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def diretorio_fonte() -> Path:
    """
    Diretorio do Symile-MIMIC bruto (a pasta `1.0.0`).

    Procura na variavel de ambiente SYMILE_MIMIC_DIR e, em seguida, no .env
    da raiz do repositorio.

    Raises:
        FileNotFoundError: se a variavel nao estiver definida ou apontar para
                           um caminho inexistente.
    """
    bruto = os.environ.get(ENV_VAR_FONTE) or _ler_dotenv(REPO_ROOT / ".env").get(
        ENV_VAR_FONTE
    )
    if not bruto:
        raise FileNotFoundError(
            f"Defina {ENV_VAR_FONTE} apontando para a pasta '1.0.0' do "
            f"Symile-MIMIC. Copie .env.example para .env e ajuste o caminho."
        )
    caminho = Path(bruto).expanduser()
    if not caminho.is_dir():
        raise FileNotFoundError(
            f"{ENV_VAR_FONTE} aponta para um caminho inexistente: {caminho}"
        )
    return caminho
