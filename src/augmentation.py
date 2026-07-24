"""
Augmentation das radiografias reais para ampliar o conjunto de avaliacao.

Do material disponibilizado so 46 radiografias vieram integras (ver
data/README.md). Para termos um conjunto de benchmark de visao maior -- e ainda
assim ancorado em dados reais -- geramos variacoes das CXR reais preservando os
achados CheXpert, que sao o ground-truth usado pelo benchmark (src/benchmark).

Regra clinica das transformacoes: so aplicamos augmentations que NAO invalidam o
rotulo. Rotacoes pequenas, variacao de brilho/contraste/gama, leve zoom-crop e
ruido gaussiano simulam variacao de aquisicao e mantem os achados. NAO aplicamos
espelhamento horizontal: ele inverte a lateralidade (coracao para o lado errado)
e tornaria rotulos como Cardiomegaly ou Pleural Effusion inconsistentes.

Cada variacao e deterministica por (paciente, indice), como o mock em src/mock.py,
para que o conjunto aumentado seja reprodutivel.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from . import config, loaders

# Diretorio do conjunto aumentado. Ignorado pelo Git, como o subconjunto base.
SUBSET_AUG_DIR = config.DATA_DIR / "symile-mimic-aug"
ARQUIVO_INDICE_AUG = "index.csv"
ARQUIVO_CXR_AUG = "chest_xray.png"

# Numero de variacoes geradas por radiografia real (alem da original).
N_VARIACOES_PADRAO = 4


@dataclass
class ParametrosAug:
    """Uma combinacao de transformacoes label-preserving para uma variacao."""

    rotacao_graus: float
    brilho: float
    contraste: float
    gama: float
    zoom: float
    ruido_std: float

    def descricao(self) -> str:
        return (
            f"rot={self.rotacao_graus:+.1f} bri={self.brilho:.2f} "
            f"con={self.contraste:.2f} gam={self.gama:.2f} "
            f"zoom={self.zoom:.2f} ruido={self.ruido_std:.3f}"
        )


def _semente(identificador: str) -> np.random.Generator:
    """Gerador deterministico por identificador (mesmo padrao de src/mock.py)."""
    digest = hashlib.blake2b(identificador.encode("utf-8"), digest_size=4).digest()
    return np.random.default_rng(int.from_bytes(digest, "big"))


def _sortear_parametros(rng: np.random.Generator) -> ParametrosAug:
    """Sorteia transformacoes dentro de faixas que preservam o rotulo clinico."""
    return ParametrosAug(
        rotacao_graus=float(rng.uniform(-8, 8)),
        brilho=float(rng.uniform(0.85, 1.15)),
        contraste=float(rng.uniform(0.85, 1.15)),
        gama=float(rng.uniform(0.85, 1.15)),
        zoom=float(rng.uniform(1.0, 1.12)),
        ruido_std=float(rng.uniform(0.0, 0.02)),
    )


def _aplicar_zoom(imagem: Image.Image, zoom: float) -> Image.Image:
    """Zoom central: recorta o centro e reescala para o tamanho original."""
    if zoom <= 1.0:
        return imagem
    lado = imagem.width
    novo = int(lado / zoom)
    canto = (lado - novo) // 2
    recorte = imagem.crop((canto, canto, canto + novo, canto + novo))
    return recorte.resize((lado, lado), Image.BILINEAR)


def aplicar(imagem: Image.Image, parametros: ParametrosAug) -> Image.Image:
    """
    Aplica uma combinacao de transformacoes label-preserving a uma radiografia.

    A ordem (geometria -> fotometria -> ruido) segue o que aconteceria na
    aquisicao real: primeiro posicionamento/enquadramento, depois exposicao,
    por fim ruido do sensor.
    """
    from PIL import ImageEnhance

    img = imagem.convert("RGB")

    # Geometria: rotacao com preenchimento cinza (borda plausivel de CXR) e zoom.
    img = img.rotate(
        parametros.rotacao_graus, resample=Image.BILINEAR, fillcolor=(16, 16, 18)
    )
    img = _aplicar_zoom(img, parametros.zoom)

    # Fotometria: brilho, contraste e correcao de gama.
    img = ImageEnhance.Brightness(img).enhance(parametros.brilho)
    img = ImageEnhance.Contrast(img).enhance(parametros.contraste)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = np.power(np.clip(arr, 0, 1), parametros.gama)

    # Ruido gaussiano do sensor.
    if parametros.ruido_std > 0:
        arr = arr + np.random.default_rng(0).normal(0, parametros.ruido_std, arr.shape)

    arr = np.clip(arr, 0, 1)
    return Image.fromarray((arr * 255).astype(np.uint8), "RGB")


def variacoes_de(
    paciente_id: str, n_variacoes: int = N_VARIACOES_PADRAO, base: Path | None = None
) -> list[tuple[str, Image.Image, ParametrosAug | None]]:
    """
    Gera a original + N variacoes de um paciente com radiografia real.

    Returns:
        Lista de (variacao_id, imagem, parametros). A original vem com
        parametros=None; as variacoes com os parametros usados.
    """
    original = loaders.carregar_radiografia(paciente_id, base)
    resultado: list[tuple[str, Image.Image, ParametrosAug | None]] = [
        (f"{paciente_id}", original.convert("RGB"), None)
    ]
    rng = _semente(paciente_id)
    for i in range(1, n_variacoes + 1):
        parametros = _sortear_parametros(rng)
        resultado.append((f"{paciente_id}_aug{i}", aplicar(original, parametros), parametros))
    return resultado


def gerar_conjunto_aumentado(
    n_variacoes: int = N_VARIACOES_PADRAO,
    base: Path | None = None,
    destino: Path | None = None,
) -> pd.DataFrame:
    """
    Materializa o conjunto aumentado em disco, apenas para os casos com CXR real.

    Para cada caso com radiografia verdadeira, salva a original e N variacoes em
    `destino/<variacao_id>/chest_xray.png` e escreve um index.csv com a
    procedencia e o paciente de origem (para recuperar os achados CheXpert).

    Returns:
        O indice do conjunto aumentado (tambem salvo como index.csv).
    """
    destino = destino or SUBSET_AUG_DIR
    destino.mkdir(parents=True, exist_ok=True)

    indice_base = loaders.listar_pacientes(base)
    reais = indice_base[indice_base["cxr_real"]]

    linhas = []
    for paciente_id in reais["paciente_id"]:
        for variacao_id, imagem, parametros in variacoes_de(paciente_id, n_variacoes, base):
            pasta = destino / variacao_id
            pasta.mkdir(parents=True, exist_ok=True)
            imagem.save(pasta / ARQUIVO_CXR_AUG)
            linhas.append(
                {
                    "variacao_id": variacao_id,
                    "paciente_id": paciente_id,
                    "e_original": parametros is None,
                    "parametros": "" if parametros is None else parametros.descricao(),
                }
            )

    indice = pd.DataFrame(linhas)
    indice.to_csv(destino / ARQUIVO_INDICE_AUG, index=False)
    return indice


def listar_variacoes(destino: Path | None = None) -> pd.DataFrame:
    """Indice do conjunto aumentado ja materializado."""
    destino = destino or SUBSET_AUG_DIR
    caminho = destino / ARQUIVO_INDICE_AUG
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Conjunto aumentado nao encontrado em {destino}. "
            f"Gere-o com: python -m src.augmentation"
        )
    return pd.read_csv(caminho)


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Gera o conjunto aumentado das radiografias reais."
    )
    parser.add_argument(
        "--n-variacoes",
        type=int,
        default=N_VARIACOES_PADRAO,
        help=f"Variacoes por radiografia real (padrao: {N_VARIACOES_PADRAO}).",
    )
    args = parser.parse_args()

    indice = gerar_conjunto_aumentado(n_variacoes=args.n_variacoes)
    n_reais = indice["e_original"].sum()
    print(
        f"Conjunto aumentado gerado: {len(indice)} imagens "
        f"({n_reais} reais x {args.n_variacoes} variacoes) em {SUBSET_AUG_DIR}"
    )


if __name__ == "__main__":
    _main()
