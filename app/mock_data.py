"""Casos clinicos ficticios usados pela interface. Nenhum dado real do Symile-MIMIC."""

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter

PACIENTES = {
    "patient_0001": {
        "demografia": {"idade": 63, "sexo": "Masculino", "altura_cm": 172, "peso_kg": 84, "admissao": "03/06/2026 14:20"},
        "sinais_vitais": {"FC (bpm)": 102, "PA (mmHg)": "148/92", "FR (irpm)": 22, "SpO₂ (%)": 93, "Temp (°C)": 36.8},
        "clinica": {
            "queixa_principal": "Dor torácica opressiva há 2 horas, com irradiação para o membro superior esquerdo.",
            "historia": "Paciente hipertenso e diabético, tabagista (30 maços-ano). Refere início súbito da dor em repouso, "
                        "acompanhada de sudorese e náuseas. Nega episódios prévios semelhantes.",
            "comorbidades": ["Hipertensão arterial", "Diabetes mellitus tipo 2", "Tabagismo"],
            "medicacoes": ["Losartana 50 mg", "Metformina 850 mg", "AAS 100 mg"],
            "alergias": "Nega alergias medicamentosas.",
        },
        "ecg": {"fc": 102, "ritmo": "Sinusal taquicárdico", "seed": 11,
                "obs": "Alterações discretas de repolarização em derivações anteriores."},
        "xray": {"seed": 11, "cardiomegalia": True, "consolidacao": None,
                 "impressao": "Índice cardiotorácico no limite superior da normalidade; campos pulmonares sem consolidações."},
        "lab": [
            ("Troponina I", "1,8", "ng/mL", "< 0,04", "↑"),
            ("CK-MB", "38", "U/L", "< 25", "↑"),
            ("Hemoglobina", "14,1", "g/dL", "13,5 – 17,5", ""),
            ("Leucócitos", "9.800", "/µL", "4.000 – 11.000", ""),
            ("Glicose", "182", "mg/dL", "70 – 99", "↑"),
            ("Creatinina", "1,1", "mg/dL", "0,7 – 1,3", ""),
            ("Potássio", "4,2", "mEq/L", "3,5 – 5,0", ""),
            ("PCR", "8", "mg/L", "< 5", "↑"),
        ],
        "relatorio": {
            "resumo": "Homem de 63 anos, hipertenso, diabético e tabagista, admitido com dor torácica opressiva de início "
                      "súbito, irradiada para o membro superior esquerdo, associada a sudorese e taquicardia.",
            "achados": [
                "Troponina I e CK-MB elevadas, sugerindo lesão miocárdica (laboratório).",
                "ECG com ritmo sinusal taquicárdico e alterações discretas de repolarização anterior.",
                "Radiografia com área cardíaca no limite superior, sem consolidações pulmonares.",
                "Hiperglicemia (182 mg/dL) compatível com DM2 descompensado no contexto agudo.",
            ],
            "hipoteses": [
                "Síndrome coronariana aguda (hipótese educacional principal).",
                "Angina instável / dor torácica de origem isquêmica.",
            ],
            "justificativa": "A combinação de fatores de risco cardiovascular, quadro clínico típico, biomarcadores de necrose "
                             "miocárdica elevados e alterações eletrocardiográficas de repolarização apoia a hipótese isquêmica. "
                             "A radiografia afasta causas pulmonares evidentes para a dor.",
            "exames_sugeridos": [
                "Curva seriada de troponina",
                "Ecocardiograma transtorácico",
                "Cineangiocoronariografia (avaliação da equipe assistente)",
            ],
        },
    },
    "patient_0002": {
        "demografia": {"idade": 45, "sexo": "Feminino", "altura_cm": 161, "peso_kg": 66, "admissao": "05/06/2026 09:47"},
        "sinais_vitais": {"FC (bpm)": 96, "PA (mmHg)": "118/76", "FR (irpm)": 26, "SpO₂ (%)": 91, "Temp (°C)": 38.7},
        "clinica": {
            "queixa_principal": "Febre, tosse produtiva e dor torácica ventilatório-dependente há 4 dias.",
            "historia": "Paciente previamente hígida, com quadro gripal há uma semana que evoluiu com febre alta, tosse com "
                        "expectoração amarelada e dispneia progressiva aos esforços.",
            "comorbidades": ["Nega comorbidades"],
            "medicacoes": ["Dipirona (uso eventual)"],
            "alergias": "Alergia a penicilina (relatada).",
        },
        "ecg": {"fc": 96, "ritmo": "Sinusal", "seed": 22,
                "obs": "Traçado sem alterações significativas."},
        "xray": {"seed": 22, "cardiomegalia": False, "consolidacao": (0.31, 0.58),
                 "impressao": "Opacidade heterogênea em base pulmonar direita, compatível com processo consolidativo."},
        "lab": [
            ("Leucócitos", "16.400", "/µL", "4.000 – 11.000", "↑"),
            ("Bastonetes", "8", "%", "< 5", "↑"),
            ("PCR", "142", "mg/L", "< 5", "↑"),
            ("Hemoglobina", "12,8", "g/dL", "12,0 – 15,5", ""),
            ("Plaquetas", "310.000", "/µL", "150.000 – 450.000", ""),
            ("Creatinina", "0,9", "mg/dL", "0,6 – 1,1", ""),
            ("Lactato", "1,9", "mmol/L", "0,5 – 2,2", ""),
        ],
        "relatorio": {
            "resumo": "Mulher de 45 anos, previamente hígida, com quadro de febre, tosse produtiva e dispneia há 4 dias, "
                      "apresentando taquipneia e queda de saturação na admissão.",
            "achados": [
                "Radiografia com opacidade em base pulmonar direita, sugestiva de consolidação.",
                "Leucocitose com desvio à esquerda e PCR muito elevada (perfil inflamatório/infeccioso).",
                "ECG sem alterações significativas.",
                "SpO₂ de 91% em ar ambiente, indicando comprometimento da troca gasosa.",
            ],
            "hipoteses": [
                "Pneumonia adquirida na comunidade (hipótese educacional principal).",
                "Derrame pleural parapneumônico associado (a investigar).",
            ],
            "justificativa": "O conjunto de achados clínicos (febre, tosse produtiva, taquipneia), laboratoriais (leucocitose, "
                             "PCR elevada) e radiológicos (consolidação em base direita) forma um padrão coerente de infecção "
                             "respiratória baixa. A alergia relatada a penicilina é relevante para a conduta da equipe.",
            "exames_sugeridos": [
                "Hemoculturas e cultura de escarro",
                "Gasometria arterial",
                "Ultrassonografia ou TC de tórax se evolução desfavorável",
            ],
        },
    },
    "patient_0003": {
        "demografia": {"idade": 71, "sexo": "Masculino", "altura_cm": 168, "peso_kg": 91, "admissao": "08/06/2026 22:05"},
        "sinais_vitais": {"FC (bpm)": 118, "PA (mmHg)": "102/64", "FR (irpm)": 28, "SpO₂ (%)": 88, "Temp (°C)": 36.4},
        "clinica": {
            "queixa_principal": "Dispneia progressiva há 5 dias, com ortopneia e edema de membros inferiores.",
            "historia": "Portador de insuficiência cardíaca com fração de ejeção reduzida e fibrilação atrial permanente. "
                        "Relata abandono das medicações há cerca de 3 semanas e ganho de peso recente.",
            "comorbidades": ["Insuficiência cardíaca (FEr)", "Fibrilação atrial", "Doença renal crônica estágio 3"],
            "medicacoes": ["Furosemida 40 mg", "Carvedilol 12,5 mg", "Varfarina 5 mg (em uso irregular)"],
            "alergias": "Nega alergias medicamentosas.",
        },
        "ecg": {"fc": 118, "ritmo": "Fibrilação atrial (RR irregular)", "seed": 33,
                "obs": "Resposta ventricular elevada, ausência de onda P."},
        "xray": {"seed": 33, "cardiomegalia": True, "consolidacao": (0.66, 0.52),
                 "impressao": "Cardiomegalia importante com sinais de congestão pulmonar e opacidade perihilar."},
        "lab": [
            ("BNP", "1.450", "pg/mL", "< 100", "↑"),
            ("Creatinina", "1,9", "mg/dL", "0,7 – 1,3", "↑"),
            ("Ureia", "78", "mg/dL", "15 – 45", "↑"),
            ("Potássio", "5,3", "mEq/L", "3,5 – 5,0", "↑"),
            ("Sódio", "131", "mEq/L", "135 – 145", "↓"),
            ("Hemoglobina", "11,2", "g/dL", "13,5 – 17,5", "↓"),
            ("INR", "1,4", "", "2,0 – 3,0 (alvo)", "↓"),
        ],
        "relatorio": {
            "resumo": "Homem de 71 anos, cardiopata crônico com fibrilação atrial, admitido com dispneia progressiva, "
                      "ortopneia e edema periférico após abandono do tratamento, em provável descompensação aguda.",
            "achados": [
                "BNP acentuadamente elevado, compatível com sobrecarga volêmica.",
                "Radiografia com cardiomegalia e sinais de congestão pulmonar.",
                "ECG em fibrilação atrial com resposta ventricular elevada.",
                "Piora de função renal, hiponatremia e hipercalemia leve; INR abaixo do alvo terapêutico.",
            ],
            "hipoteses": [
                "Insuficiência cardíaca agudamente descompensada (hipótese educacional principal).",
                "Síndrome cardiorrenal associada.",
            ],
            "justificativa": "A tríade de história de má adesão terapêutica, exame físico congestivo e BNP elevado, somada aos "
                             "achados radiográficos de congestão e à FA com alta resposta ventricular, sustenta o quadro de "
                             "descompensação. A disfunção renal em progressão sugere componente cardiorrenal.",
            "exames_sugeridos": [
                "Ecocardiograma transtorácico",
                "Eletrólitos e função renal seriados",
                "Monitorização do balanço hídrico e do peso diário",
            ],
        },
    },
}


def rotulo_paciente(pid: str) -> str:
    d = PACIENTES[pid]["demografia"]
    return f"{pid} — {d['sexo'][0]}, {d['idade']} anos"


def tabela_laboratorio(pid: str) -> pd.DataFrame:
    linhas = PACIENTES[pid]["lab"]
    df = pd.DataFrame(linhas, columns=["Exame", "Resultado", "Unidade", "Referência", "Alteração"])
    df["Alteração"] = df["Alteração"].map({"↑": "↑ Acima", "↓": "↓ Abaixo", "": "Normal"})
    return df


def gerar_ecg(seed: int, fc: int, irregular: bool = False, duracao_s: float = 10.0, fs: int = 250):
    rng = np.random.default_rng(seed)
    t = np.arange(0, duracao_s, 1 / fs)
    sinal = np.zeros_like(t)

    rr_medio = 60.0 / fc
    batidas, tk = [], 0.3
    while tk < duracao_s:
        batidas.append(tk)
        jitter = 0.18 if irregular else 0.02
        tk += rr_medio * (1 + rng.normal(0, jitter))

    def onda(centro, amplitude, largura):
        return amplitude * np.exp(-((t - centro) ** 2) / (2 * largura**2))

    for b in batidas:
        if not irregular:
            sinal += onda(b - 0.20, 0.12, 0.045)
        sinal += onda(b - 0.028, -0.16, 0.012)
        sinal += onda(b, 1.05, 0.016)
        sinal += onda(b + 0.030, -0.24, 0.014)
        sinal += onda(b + 0.26, 0.32, 0.060)

    sinal += 0.045 * np.sin(2 * np.pi * 0.28 * t)
    sinal += rng.normal(0, 0.012, t.shape)
    return t, sinal


def gerar_radiografia(seed: int, cardiomegalia: bool = False, consolidacao=None) -> Image.Image:
    rng = np.random.default_rng(seed)
    h, w = 560, 480
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    xn, yn = xx / w, yy / h

    img = 0.22 + 0.55 * np.exp(-((xn - 0.5) ** 2) / 0.09)
    img -= 0.30 * np.exp(-((yn - 0.02) ** 2) / 0.01)

    for cx in (0.32, 0.68):
        pulmao = np.exp(-(((xn - cx) / 0.135) ** 2 + ((yn - 0.42) / 0.235) ** 2))
        img -= 0.34 * pulmao

    raio_coracao = 0.21 if cardiomegalia else 0.15
    coracao = np.exp(-(((xn - 0.57) / raio_coracao) ** 2 + ((yn - 0.60) / 0.145) ** 2))
    img += 0.30 * coracao

    for i in range(7):
        yc = 0.16 + 0.088 * i
        curva = yc + 0.055 * np.sin((xn - 0.5) * np.pi)
        costela = np.exp(-((yn - curva) ** 2) / 0.00010)
        img += 0.055 * costela * (np.abs(xn - 0.5) < 0.43)

    img += 0.24 * (yn > 0.80 + 0.05 * np.sin(xn * np.pi))

    if consolidacao is not None:
        cx, cy = consolidacao
        img += 0.26 * np.exp(-(((xn - cx) / 0.085) ** 2 + ((yn - cy) / 0.10) ** 2))

    img += rng.normal(0, 0.022, img.shape)
    img = np.clip(img, 0, 1)
    return Image.fromarray((img * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2))
