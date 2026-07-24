"""
Orquestrador do benchmark: roda os modelos disponiveis sobre as amostras e
gera os relatorios comparativos.

Amostras: apenas casos com radiografia REAL (o ground-truth CheXpert so faz
sentido sobre imagem verdadeira). Com --com-aug, inclui tambem as variacoes
geradas por src/augmentation, que herdam os rotulos do caso de origem.

Sem chaves de API configuradas, nenhum modelo roda -- o ambiente fica pronto e o
benchmark reporta o que falta. Assim da para preparar tudo antes de ter as
chaves e, quando elas chegarem no .env, e so rodar de novo.
"""

import dataclasses
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .. import config, loaders, augmentation
from ..llm import catalogo, prompt as prompt_mod
from ..llm.base import ClienteLLM, ErroLLM
from . import metricas

# Onde os resultados sao salvos (ignorado pelo Git, como os demais artefatos).
RESULTADOS_DIR = config.REPO_ROOT / "benchmark_resultados"


@dataclasses.dataclass
class Amostra:
    """Um item de benchmark: um caso e o ground-truth CheXpert dele."""

    item_id: str
    caso: loaders.Caso
    ground_truth: dict[str, str]


def montar_amostras(
    usar_aug: bool = False, base: Path | None = None, limite: int | None = None
) -> list[Amostra]:
    """Monta as amostras de benchmark a partir dos casos com radiografia real."""
    indice = loaders.listar_pacientes(base)
    reais = indice[indice["cxr_real"]]["paciente_id"].tolist()

    amostras: list[Amostra] = []
    for paciente_id in reais:
        caso = loaders.carregar_caso(paciente_id, base)
        gt = metricas.ground_truth_do_caso(caso.dados_clinicos)
        if not gt:
            continue  # sem rotulo CheXpert nao ha o que pontuar
        amostras.append(Amostra(paciente_id, caso, gt))

        if usar_aug:
            amostras.extend(_amostras_aug(paciente_id, caso, gt))

    if limite is not None:
        amostras = amostras[:limite]
    return amostras


def _amostras_aug(
    paciente_id: str, caso_base: loaders.Caso, gt: dict[str, str]
) -> list[Amostra]:
    """Variacoes aumentadas de um caso, se o conjunto aumentado ja existir."""
    try:
        indice_aug = augmentation.listar_variacoes()
    except FileNotFoundError:
        return []
    variacoes = indice_aug[
        (indice_aug["paciente_id"] == paciente_id) & (~indice_aug["e_original"])
    ]
    saida = []
    for variacao_id in variacoes["variacao_id"]:
        caminho = augmentation.SUBSET_AUG_DIR / variacao_id / augmentation.ARQUIVO_CXR_AUG
        if not caminho.is_file():
            continue
        imagem = Image.open(caminho).convert("RGB")
        caso_aug = dataclasses.replace(
            caso_base, paciente_id=variacao_id, radiografia=imagem
        )
        saida.append(Amostra(variacao_id, caso_aug, gt))
    return saida


def rodar(
    chaves: list[str] | None = None,
    usar_aug: bool = False,
    limite: int | None = None,
    max_tokens: int = 2000,
    base: Path | None = None,
    destino: Path | None = None,
) -> list[metricas.AgregadoModelo]:
    """
    Roda o benchmark e devolve os agregados por modelo (tambem salvos em disco).
    """
    destino = destino or RESULTADOS_DIR
    destino.mkdir(parents=True, exist_ok=True)

    config.carregar_env()  # traz as chaves do .env para os.environ
    candidatos = catalogo.disponiveis(catalogo.selecionar(chaves))
    if not candidatos:
        print("Nenhum modelo disponivel: configure as chaves de API no .env.")
        print(_texto_status_chaves())
        return []

    amostras = montar_amostras(usar_aug=usar_aug, base=base, limite=limite)
    if not amostras:
        print("Nenhuma amostra com ground-truth CheXpert encontrada.")
        return []

    print(
        f"Benchmark: {len(candidatos)} modelo(s) x {len(amostras)} amostra(s)"
        f"{' (com augmentation)' if usar_aug else ''}."
    )

    agregados: list[metricas.AgregadoModelo] = []
    for candidato in candidatos:
        agregado = _rodar_modelo(candidato, amostras, max_tokens, destino)
        if agregado is not None:
            agregados.append(agregado)

    agregados.sort(key=lambda a: a.f1, reverse=True)
    _salvar_resumo(agregados, amostras, usar_aug, destino)
    return agregados


def _rodar_modelo(
    candidato: catalogo.ModeloCandidato,
    amostras: list[Amostra],
    max_tokens: int,
    destino: Path,
) -> metricas.AgregadoModelo | None:
    """Roda um modelo sobre todas as amostras e salva as respostas brutas."""
    try:
        cliente: ClienteLLM = candidato.instanciar()
    except ErroLLM as exc:
        print(f"  [{candidato.chave}] indisponivel: {exc}")
        return None

    print(f"  [{candidato.chave}] {candidato.modelo} ...", end="", flush=True)
    metricas_caso: list[metricas.MetricasCaso] = []
    respostas_brutas = []
    for amostra in amostras:
        prompt = prompt_mod.montar_prompt(amostra.caso)
        resposta = cliente.gerar(prompt, max_tokens=max_tokens)
        m = metricas.avaliar_caso(resposta, amostra.ground_truth)
        m.custo_usd = candidato.custo_usd(
            resposta.tokens_entrada, resposta.tokens_saida
        )
        metricas_caso.append(m)
        respostas_brutas.append(
            {
                "item_id": amostra.item_id,
                "ground_truth": amostra.ground_truth,
                "ok": resposta.ok,
                "erro": resposta.erro,
                "latencia_s": round(resposta.latencia_s, 3),
                "tokens_entrada": resposta.tokens_entrada,
                "tokens_saida": resposta.tokens_saida,
                "achados_estimados": (
                    resposta.relatorio.achados_radiologicos if resposta.relatorio else None
                ),
            }
        )

    agregado = metricas.agregar(
        candidato.chave, candidato.provedor, candidato.modelo, metricas_caso
    )
    (destino / f"respostas_{candidato.chave}.json").write_text(
        json.dumps(respostas_brutas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f" F1={agregado.f1:.3f} acc={agregado.acuracia:.3f} "
        f"falhas={agregado.n_falhas}/{agregado.n_casos}"
    )
    return agregado


def _texto_status_chaves() -> str:
    linhas = ["Status das chaves de API (defina no .env):"]
    for prov, definida in catalogo.status_chaves().items():
        env = catalogo.ENV_POR_PROVEDOR[prov]
        marca = "OK" if definida else "faltando"
        linhas.append(f"  - {prov:10s} {env:20s} [{marca}]")
    return "\n".join(linhas)


def _salvar_resumo(
    agregados: list[metricas.AgregadoModelo],
    amostras: list[Amostra],
    usar_aug: bool,
    destino: Path,
) -> None:
    """Salva o CSV e o relatorio markdown comparativo."""
    import csv

    resumos = [a.resumo() for a in agregados]

    # CSV
    caminho_csv = destino / "resumo.csv"
    if resumos:
        with caminho_csv.open("w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(resumos[0].keys()))
            escritor.writeheader()
            escritor.writerows(resumos)

    # Markdown
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    linhas = [
        "# Benchmark de LLMs multimodais — ClinicalFusion",
        "",
        f"- Gerado em: {agora}",
        f"- Amostras: {len(amostras)}" + (" (com augmentation)" if usar_aug else ""),
        "- Metrica principal: F1 dos achados CheXpert (classe 'positivo').",
        "",
        "| # | Modelo | Provedor | F1 | Precisao | Recall | Acuracia | Completude | Latencia (s) | Custo medio (USD) | Falhas |",
        "|---|--------|----------|----|----------|--------|----------|-----------|--------------|-------------------|--------|",
    ]
    for i, a in enumerate(agregados, 1):
        r = a.resumo()
        linhas.append(
            f"| {i} | {r['chave']} | {r['provedor']} | {r['f1']} | {r['precisao']} | "
            f"{r['recall']} | {r['acuracia']} | {r['completude']} | "
            f"{r['latencia_media_s']} | {r['custo_medio_usd']:.6f} | "
            f"{r['n_falhas']}/{r['n_casos']} |"
        )
    if agregados:
        vencedor = agregados[0]
        linhas += [
            "",
            f"**Melhor F1:** `{vencedor.chave}` ({vencedor.modelo}) "
            f"com F1={vencedor.f1:.3f}.",
        ]
    linhas.append("")
    (destino / "relatorio.md").write_text("\n".join(linhas), encoding="utf-8")
    print(f"Resumo salvo em {destino}")


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark de LLMs multimodais.")
    parser.add_argument(
        "--modelos",
        nargs="*",
        default=None,
        help="Chaves do catalogo a comparar (padrao: um por provedor).",
    )
    parser.add_argument(
        "--com-aug", action="store_true", help="Inclui as variacoes aumentadas."
    )
    parser.add_argument(
        "--limite", type=int, default=None, help="Limita o numero de amostras."
    )
    parser.add_argument("--max-tokens", type=int, default=2000)
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista o catalogo e o status das chaves e sai.",
    )
    args = parser.parse_args()

    config.carregar_env()  # garante que --listar reflita as chaves do .env
    if args.listar:
        print("Catalogo de modelos:")
        for m in catalogo.CATALOGO:
            marca = "disponivel" if m.disponivel() else f"precisa de {m.env_var}"
            print(f"  {m.chave:14s} {m.provedor:10s} {m.modelo:22s} [{marca}]")
        print()
        print(_texto_status_chaves())
        return

    rodar(
        chaves=args.modelos,
        usar_aug=args.com_aug,
        limite=args.limite,
        max_tokens=args.max_tokens,
    )


if __name__ == "__main__":
    _main()
