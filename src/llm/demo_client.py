"""
Cliente de DEMONSTRACAO: produz um relatorio simulado, sem chamar API nenhuma.

Existe para uma unica finalidade: permitir apresentar a interface de ponta a
ponta quando as chaves de API estao indisponiveis (sem credito, projeto
bloqueado, sem rede). Ele percorre exatamente o mesmo caminho de um cliente
real -- monta o JSON do relatorio e o entrega a `ClienteLLM._finalizar`, que
parseia com `RelatorioClinico.do_json` --, entao o que aparece na tela exercita
o codigo de verdade; so a inferencia e falsa.

NADA aqui e uma analise clinica: o texto e um molde fixo e os achados
radiologicos sao PSEUDOALEATORIOS, derivados de um hash do proprio prompt. Duas
consequencias deliberadas:

1. Todo texto visivel vem marcado com "[SIMULADO]" e o campo `aviso` diz que o
   conteudo nao foi produzido por um modelo. Ninguem deve confundir a tela de
   demonstracao com um relatorio real.
2. O cliente NAO tem acesso ao ground-truth do caso (o `PromptMultimodal` nao
   carrega os achados CheXpert rotulados), entao rodar o benchmark contra ele
   produz uma nota aleatoria -- e nao uma nota artificialmente perfeita. Ainda
   assim ele fica FORA de `CHAVES_PADRAO`, e so aparece no catalogo quando
   `CLINICALFUSION_DEMO` esta definida no ambiente.

Uso:
    # PowerShell
    $env:CLINICALFUSION_DEMO = "1"
    python -m streamlit run app/streamlit_app.py
"""

import hashlib
import json
import re
import time

from .. import config
from .base import ClienteLLM, RespostaLLM
from .prompt import PromptMultimodal

# Pausa curta antes de responder. Sem ela a resposta volta instantaneamente, o
# spinner da interface nem chega a aparecer e a demonstracao fica menos fiel ao
# ritmo de uma chamada real.
_ATRASO_S = 0.8

# Achados que o molde pode marcar como positivos. Restrito aos mais comuns em
# radiografia de torax para que a tela mostre algo plausivel; "No Finding" fica
# de fora porque e mutuamente exclusivo com os demais.
_ACHADOS_SORTEAVEIS = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Lung Opacity",
    "Pleural Effusion",
    "Pneumonia",
    "Support Devices",
]

_MARCA = "[SIMULADO]"

_AVISO = (
    f"{_MARCA} Este relatorio NAO foi produzido por um modelo de linguagem. "
    "E um conteudo fixo do cliente de demonstracao (src/llm/demo_client.py), "
    "usado para apresentar a interface quando as chaves de API estao "
    "indisponiveis. Os achados radiologicos sao pseudoaleatorios e nao "
    "correspondem a imagem. Nao use para nenhuma finalidade clinica."
)


def _semente(texto: str) -> int:
    """
    Semente determinista a partir dos DADOS do caso (mesmo padrao de src/mock.py).

    Semeia so pelas secoes de dados clinicos e laboratorio -- nunca pela pergunta
    do usuario, que vem no fim do prompt. Os achados de uma radiografia nao podem
    mudar conforme o que se pergunta sobre ela: assim o mesmo paciente mostra
    sempre os mesmos achados, seja qual for a pergunta.
    """
    ate_radiografia = texto.split("== 3.")[0] or texto
    digest = hashlib.blake2b(ate_radiografia.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big")


def _achados_simulados(prompt: PromptMultimodal) -> dict[str, str]:
    """
    Monta o vetor dos 14 achados CheXpert.

    Sem radiografia real o cliente marca tudo como 'indeterminado', que e o que o
    system prompt manda fazer diante de um placeholder -- assim a demonstracao
    reproduz tambem esse comportamento.
    """
    if not prompt.tem_radiografia_real:
        return {achado: "indeterminado" for achado in config.ACHADOS_CHEXPERT}

    semente = _semente(prompt.texto)
    quantos = 1 + semente % 3  # 1 a 3 positivos
    positivos = set()
    for passo in range(quantos):
        indice = (semente >> (4 * (passo + 1))) % len(_ACHADOS_SORTEAVEIS)
        positivos.add(_ACHADOS_SORTEAVEIS[indice])

    return {
        achado: "positivo" if achado in positivos else "negativo"
        for achado in config.ACHADOS_CHEXPERT
    }


def _demografia(texto: str) -> str:
    """Extrai 'Idade: X / Sexo: Y' do prompt, para o resumo citar o caso certo."""
    idade = re.search(r"Idade:\s*(\S+)", texto)
    sexo = re.search(r"Sexo:\s*(\S+)", texto)
    partes = []
    if idade and idade.group(1) != "n/d":
        partes.append(f"{idade.group(1)} anos")
    if sexo and sexo.group(1) != "n/d":
        partes.append({"M": "sexo masculino", "F": "sexo feminino"}.get(
            sexo.group(1), f"sexo {sexo.group(1)}"
        ))
    return ", ".join(partes) if partes else "demografia nao informada"


def _exames_citados(texto: str, limite: int = 3) -> list[str]:
    """Pega os primeiros exames laboratoriais listados no prompt."""
    bloco = re.search(
        r"== 2\. Exames laboratoriais medidos ==\n(.*?)\n\n", texto, re.S
    )
    if not bloco:
        return []
    nomes = re.findall(r"^- ([^:]+):", bloco.group(1), re.M)
    return nomes[:limite]


class ClienteDemonstracao(ClienteLLM):
    """Cliente que devolve um relatorio fixo, sem chamar provedor nenhum."""

    provedor = "demo"

    def __init__(self, modelo: str = "relatorio-simulado", max_tokens: int = 2000):
        super().__init__(modelo)
        self._max_tokens = max_tokens

    def gerar(self, prompt: PromptMultimodal, max_tokens: int = 2000) -> RespostaLLM:
        inicio = time.perf_counter()
        time.sleep(_ATRASO_S)

        achados = _achados_simulados(prompt)
        positivos = [a for a, v in achados.items() if v == "positivo"]
        perfil = _demografia(prompt.texto)
        exames = _exames_citados(prompt.texto)

        if prompt.tem_radiografia_real:
            frase_imagem = (
                "achados marcados: " + ", ".join(positivos)
                if positivos
                else "nenhum achado marcado"
            )
        else:
            frase_imagem = (
                "radiografia indisponivel para o caso (placeholder), todos os "
                "achados ficaram como indeterminado"
            )

        dados = {
            "resumo": (
                f"{_MARCA} Relatorio de demonstracao para um paciente de {perfil}. "
                f"Radiografia: {frase_imagem}. O conteudo abaixo e um molde fixo e "
                "nao reflete analise de nenhum modelo."
            ),
            "achados_radiologicos": achados,
            "achados_principais": (
                [f"{_MARCA} {a} (marcado pelo gerador de demonstracao)" for a in positivos]
                or [f"{_MARCA} Nenhum achado positivo neste caso simulado."]
            ),
            "hipoteses": [
                f"{_MARCA} Hipotese de exemplo 1 — ilustra o campo 'hipoteses' da interface.",
                f"{_MARCA} Hipotese de exemplo 2 — sem relacao com o caso apresentado.",
            ],
            "justificativa": (
                f"{_MARCA} Campo de justificativa preenchido com texto fixo. "
                + (
                    "Exames citados no caso: " + ", ".join(exames) + ". "
                    if exames
                    else ""
                )
                + "Em uma execucao real, aqui apareceria o encadeamento entre os "
                "achados da radiografia, os exames laboratoriais e os dados "
                "clinicos que sustenta cada hipotese."
            ),
            "exames_sugeridos": [
                f"{_MARCA} Exame sugerido de exemplo (nao e recomendacao clinica).",
            ],
            "aviso": _AVISO,
        }

        texto = json.dumps(dados, ensure_ascii=False)
        # Tokens estimados (~4 caracteres por token) so para os paineis de
        # telemetria e custo nao aparecerem vazios na demonstracao.
        entrada = (len(prompt.system) + len(prompt.texto)) // 4
        return self._finalizar(texto, inicio, entrada, len(texto) // 4)

    def conversar(self, system: str, texto: str) -> str:
        """Chamada apenas-texto (usada pela traducao para o paciente)."""
        time.sleep(_ATRASO_S)
        return (
            f"{_MARCA} Resposta de demonstracao. O cliente simulado nao reescreve "
            "nem traduz o conteudo recebido; com uma chave de API valida, este "
            "campo traria o texto adaptado pelo modelo."
        )

    def chat_caso(self, system, contexto, imagem, historico, pergunta):
        """
        Resposta simulada do modo chat.

        Returns:
            (texto, tokens_entrada, tokens_saida).
        """
        time.sleep(_ATRASO_S)
        achados = re.search(r"Achados CheXpert presentes: ([^.]+)\.", contexto or "")
        presentes = achados.group(1) if achados else "nao informados"
        resposta = (
            f"{_MARCA} Esta e uma resposta fixa do cliente de demonstracao — "
            "nenhum modelo foi consultado.\n\n"
            f"Sua pergunta foi: “{pergunta}”\n\n"
            f"Os achados registrados neste caso sao: {presentes}. "
            "Com uma chave de API ativa, o modelo responderia aqui cruzando esses "
            "achados com os exames laboratoriais e os dados clinicos do caso."
        )
        entrada = (len(system or "") + len(contexto or "") + len(pergunta)) // 4
        return resposta, entrada, len(resposta) // 4
