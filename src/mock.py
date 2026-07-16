"""
Geradores de dados sinteticos para as modalidades que nao recebemos.

Do material disponibilizado faltam o sinal bruto de ECG (nenhum `ecg_*.npy`) e
a maior parte das radiografias (`cxr_test.npy` veio truncado). Para nao travar o
desenvolvimento da interface, estas modalidades sao geradas sinteticamente,
respeitando o mesmo formato dos dados reais.

Tudo o que sai daqui e MOCK e vem marcado como tal: o ECG segue o contrato real
(12 derivacoes, 5000 amostras em [-1, 1]) para que o codigo de leitura e de
plotagem seja o mesmo dos dados reais, e a radiografia e um cartao de aviso
legivel -- deliberadamente NAO tentamos imitar uma imagem medica, que poderia
ser confundida com um exame de verdade.
"""

import hashlib

import numpy as np
from PIL import Image, ImageDraw

from . import config

# Amplitude relativa de cada derivacao em relacao a D2. aVR aparece invertida e
# V1 negativa, como em um ECG real, para que o tracado seja plausivel na tela.
_FATOR_DERIVACAO = {
    "I": 0.60,
    "II": 1.00,
    "III": 0.50,
    "aVR": -0.80,
    "aVL": 0.30,
    "aVF": 0.70,
    "V1": -0.40,
    "V2": 0.50,
    "V3": 0.80,
    "V4": 1.00,
    "V5": 0.90,
    "V6": 0.70,
}

# (centro em s a partir do inicio do batimento, amplitude, largura em s)
_ONDAS = [
    (0.10, 0.15, 0.025),  # P
    (0.16, -0.10, 0.008),  # Q
    (0.18, 1.00, 0.010),  # R
    (0.20, -0.25, 0.010),  # S
    (0.35, 0.30, 0.045),  # T
]


def _semente(identificador: str) -> np.random.Generator:
    """
    Gerador deterministico por paciente, para que o mock seja reprodutivel.

    Usa blake2b em vez de hash(), que e randomizado a cada processo e faria o
    mesmo paciente receber um ECG diferente a cada execucao.
    """
    digest = hashlib.blake2b(identificador.encode("utf-8"), digest_size=4).digest()
    return np.random.default_rng(int.from_bytes(digest, "big"))


def _batimento(eixo_t: np.ndarray) -> np.ndarray:
    """Soma das ondas P, Q, R, S e T em um unico batimento."""
    sinal = np.zeros_like(eixo_t)
    for centro, amplitude, largura in _ONDAS:
        sinal += amplitude * np.exp(-((eixo_t - centro) ** 2) / (2 * largura**2))
    return sinal


def gerar_ecg(identificador: str) -> np.ndarray:
    """
    Gera um ECG sintetico de 12 derivacoes no formato dos dados reais.

    Returns:
        Array (5000, 12) float32 normalizado em [-1, 1], como faz o
        pre-processamento original do Symile-MIMIC.
    """
    rng = _semente(identificador)
    bpm = rng.uniform(58, 95)
    intervalo_rr = 60.0 / bpm

    eixo_t = np.arange(config.ECG_N_AMOSTRAS) / config.ECG_FREQUENCIA_HZ
    fase = np.mod(eixo_t + rng.uniform(0, intervalo_rr), intervalo_rr)
    base = _batimento(fase)

    # Oscilacao lenta da linha de base, como a respiracao provoca no exame real.
    deriva = 0.05 * np.sin(2 * np.pi * 0.25 * eixo_t + rng.uniform(0, 2 * np.pi))

    sinal = np.empty(
        (config.ECG_N_AMOSTRAS, len(config.ECG_DERIVACOES)), dtype=np.float32
    )
    for coluna, derivacao in enumerate(config.ECG_DERIVACOES):
        ruido = rng.normal(0, 0.01, config.ECG_N_AMOSTRAS)
        sinal[:, coluna] = _FATOR_DERIVACAO[derivacao] * base + deriva + ruido

    minimo, maximo = sinal.min(), sinal.max()
    return (2 * (sinal - minimo) / (maximo - minimo) - 1).astype(np.float32)


def gerar_cxr_placeholder(identificador: str) -> Image.Image:
    """
    Cria o cartao que ocupa o lugar de uma radiografia ausente.

    Nao e uma imagem medica sintetica: e um aviso legivel, do mesmo tamanho das
    radiografias reais (320x320), para que ninguem confunda o placeholder com um
    exame e para que a interface nao precise tratar dois tamanhos.
    """
    lado = config.CXR_LADO
    imagem = Image.new("RGB", (lado, lado), (32, 32, 36))
    desenho = ImageDraw.Draw(imagem)

    for posicao in range(-lado, lado * 2, 26):
        desenho.line([(posicao, 0), (posicao + lado, lado)], fill=(46, 46, 52), width=8)

    desenho.rectangle([12, 12, lado - 12, lado - 12], outline=(120, 120, 130), width=2)

    linhas = [
        "RADIOGRAFIA",
        "NAO DISPONIVEL",
        "",
        "MOCK / PLACEHOLDER",
        "",
        identificador,
    ]
    altura_linha = 18
    topo = (lado - len(linhas) * altura_linha) // 2
    for indice, linha in enumerate(linhas):
        cor = (235, 235, 240) if indice < 2 else (170, 170, 180)
        desenho.text(
            (lado // 2, topo + indice * altura_linha), linha, fill=cor, anchor="mm"
        )

    return imagem
