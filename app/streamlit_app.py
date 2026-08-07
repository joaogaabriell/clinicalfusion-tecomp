"""ClinicalFusion — interface do assistente multimodal para analise de casos clinicos.

Le os casos do subconjunto do Symile-MIMIC gerado por `src.build_subset`. Os
exames laboratoriais, a demografia, os dados da admissao e os achados do
CheXpert sao reais; o ECG e sintetico e parte das radiografias tambem, porque o
material disponibilizado veio incompleto (ver `data/README.md`). A procedencia
de cada modalidade e mostrada na propria tela.

Estrutura do arquivo:
    1. CONFIGURACAO      — page_config, logo e icones SVG
    2. ESTILOS           — CSS global (cards, grids e comportamento da sidebar)
    3. DADOS E FIGURAS   — cache das modalidades e geracao do grafico do ECG
    4. RELATORIO         — geracao do relatorio via LLM (LangChain) + extras
    5. SIDEBAR           — logo, selecao do paciente e aviso educacional
    6. TELA INICIAL      — hero, modalidades e fluxo (quando nenhum caso esta selecionado)
    7. TELA DO CASO      — metricas + abas (clinica, RX, ECG, laboratorio, relatorio)
    8. SCRIPT DA SIDEBAR — JS que abre a barra lateral ao aproximar o mouse da borda
"""

import base64
import html
import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, str(Path(__file__).parent))

import dados

from datetime import datetime  # noqa: E402

from src import config, demo_subset, export_pdf, n8n  # noqa: E402
from src.llm import catalogo, chat as chat_mod, extras, prompt as prompt_mod  # noqa: E402

# Carrega as chaves de API do .env para o ambiente (os clientes leem de os.environ).
config.carregar_env()

# ---------------------------------------------------------------- 1. CONFIGURACAO

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title="ClinicalFusion",
    page_icon=str(ASSETS / "favicon.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

LOGO_B64 = base64.b64encode((ASSETS / "logo.svg").read_bytes()).decode()


def _icone(conteudo: str) -> str:
    """Envolve o traçado de um ícone Material no wrapper SVG usado nos cards."""
    return (
        '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{conteudo}</svg>"
    )


ICONES = {
    "rx": _icone(
        '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/>'
        '<path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/>'
        '<path d="M11.246 16.657a1 1 0 0 0 1.508 0l3.57-4.101A2.75 2.75 0 1 0 12 9.168a2.75 2.75 0 1 0-4.324 3.388z"/>'
    ),
    "ecg": _icone('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'),
    "lab": _icone(
        '<path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2"/>'
        '<path d="M6.453 15h11.094"/><path d="M8.5 2h7"/>'
    ),
    "clin": _icone(
        '<rect x="8" y="2" width="8" height="4" rx="1"/>'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>'
    ),
}

# ---------------------------------------------------------------- 2. ESTILOS (CSS)

st.markdown(
    """
<style>
.block-container { max-width: 1180px; padding-top: 3.6rem; padding-bottom: 0.8rem; }
.cf-hero { display: flex; align-items: center; justify-content: center; gap: 0.75rem; }
.cf-hero img { width: clamp(44px, 4.5vw, 60px); }
.cf-hero h1 { margin: 0; padding: 0; font-size: clamp(1.6rem, 3vw, 2.3rem); }
.cf-sub { text-align: center; opacity: 0.8; max-width: 900px; margin: 0.4rem auto 0;
          font-size: clamp(0.85rem, 1.1vw, 0.98rem); }
.cf-secao { text-align: center; font-weight: 600; font-size: clamp(1rem, 1.4vw, 1.2rem); margin: 1rem 0 0.7rem; }
.cf-grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.9rem; }
.cf-grid5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.8rem; }
@media (max-width: 900px) { .cf-grid4, .cf-grid5 { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 520px) { .cf-grid4, .cf-grid5 { grid-template-columns: 1fr; } }
.cf-card { border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 12px;
           padding: clamp(0.6rem, 1.2vh, 1rem) 0.7rem; text-align: center; }
.cf-card .icone { display: flex; justify-content: center; margin-bottom: 0.4rem; }
.cf-card .titulo { font-weight: 600; font-size: clamp(0.85rem, 1.1vw, 0.95rem); margin-bottom: 0.25rem; }
.cf-card .texto { font-size: clamp(0.75rem, 1vw, 0.82rem); opacity: 0.75; }
.cf-passo { width: 26px; height: 26px; border-radius: 50%; background: #0ea5e9; color: #fff; font-weight: 700;
            font-size: 0.85rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.4rem; }
/* Oculta o iframe do script auxiliar e os botoes nativos do Streamlit */
div[data-testid="stElementContainer"]:has(> iframe[height="0"]) { display: none; }
[data-testid="stAppDeployButton"] { display: none; }
[data-testid="stHeaderActionElements"] { display: none; }

/* #sidebar — barra recolhida fica como uma faixa fina; .cf-peek (via JS) a desliza para dentro */
section[data-testid="stSidebar"] { transition: transform 0.25s ease; }
section[data-testid="stSidebar"][aria-expanded="false"] {
    visibility: visible !important;
    position: fixed !important; top: 0; left: 0; height: 100vh !important; z-index: 1000;
    width: 21rem !important; min-width: 21rem !important;
    transform: translateX(calc(16px - 100%)) !important;
}
section[data-testid="stSidebar"][aria-expanded="false"]::after {
    content: ""; position: absolute; top: 0; right: 0; width: 4px; height: 100%;
    background: linear-gradient(180deg, #0ea5e9, #0f766e);
}
section[data-testid="stSidebar"][aria-expanded="false"].cf-peek {
    transform: translateX(0) !important;
    box-shadow: 8px 0 24px rgba(0, 0, 0, 0.35);
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- 3. DADOS E FIGURAS


@st.cache_data
def indice_cache():
    return dados.listar_casos()


@st.cache_resource
def caso_cache(pid: str):
    """As quatro modalidades do paciente. `cache_resource` porque a imagem PIL não é serializável."""
    return dados.carregar(pid)


def figura_ecg(pid: str, derivacao: str, altura: float = 3.2):
    """Traçado do ECG sobre o papel milimetrado (0,04 s por quadradinho menor)."""
    ecg = caso_cache(pid).ecg
    fig, ax = plt.subplots(figsize=(11, altura))
    ax.set_facecolor("#fff7f7")
    ax.xaxis.set_major_locator(MultipleLocator(0.2))
    ax.xaxis.set_minor_locator(MultipleLocator(0.04))
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(MultipleLocator(0.1))
    ax.grid(which="major", color="#f1a5a5", linewidth=0.7)
    ax.grid(which="minor", color="#fadcdc", linewidth=0.4)
    ax.plot(ecg["tempo_s"], ecg[derivacao], color="#1a1a1a", linewidth=0.9)
    ax.set_xlim(0, ecg["tempo_s"].iloc[-1])
    ax.set_ylim(-1.15, 1.15)
    ax.set_xlabel("Tempo (s)")
    # O sinal chega normalizado em [-1, 1] pelo pre-processamento do Symile-MIMIC,
    # entao o eixo nao esta em mV.
    ax.set_ylabel("Amplitude (normalizada)")
    ax.set_title(f"Derivação {derivacao} — 10 s @ 500 Hz", fontsize=10, loc="left")
    fig.tight_layout()
    return fig


@st.cache_data(show_spinner=False)
def ecg_png(pid: str, derivacao: str, altura: float = 3.2) -> bytes:
    """Renderiza o ECG como PNG estavel e libera a figura do Matplotlib."""
    figura = figura_ecg(pid, derivacao, altura)
    buffer = io.BytesIO()
    try:
        figura.savefig(
            buffer,
            format="png",
            dpi=160,
            bbox_inches="tight",
            metadata={"Software": "ClinicalFusion"},
        )
    finally:
        plt.close(figura)
    return buffer.getvalue()


@st.cache_data(show_spinner=False)
def radiografia_png(pid: str) -> bytes:
    """Converte a radiografia para PNG antes de embuti-la na pagina."""
    buffer = io.BytesIO()
    caso_cache(pid).radiografia.save(buffer, format="PNG")
    return buffer.getvalue()


def exibir_png(conteudo: bytes, alt: str, legenda: str | None = None) -> None:
    """Exibe PNG em data URI, sem depender do armazenamento /media do Streamlit."""
    origem = base64.b64encode(conteudo).decode("ascii")
    legenda_html = (
        f'<figcaption style="margin-top:.35rem;opacity:.7;font-size:.85rem">'
        f"{html.escape(legenda)}</figcaption>"
        if legenda
        else ""
    )
    st.markdown(
        '<figure style="margin:0;text-align:center">'
        f'<img src="data:image/png;base64,{origem}" alt="{html.escape(alt)}" '
        'style="display:block;width:100%;height:auto;border-radius:.35rem">'
        f"{legenda_html}</figure>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- 4. RELATORIO (LLM)


def gerar_relatorio(caso, pergunta: str | None, candidato):
    """
    Chama o LLM escolhido (via LangChain) e devolve a RespostaLLM.

    `pergunta=None` e o fluxo padrao da interface: o relatorio sai completo com
    um clique, guiado pelo system prompt (ver src/llm/prompt.py). A comparacao
    entre casos ainda passa uma pergunta, porque ali ela e o criterio comum aos
    dois relatorios.
    """
    cliente = candidato.instanciar()
    prompt = prompt_mod.montar_prompt(caso, pergunta)
    return cliente.gerar(prompt)


def arquivar_no_drive(paciente_id: str, resposta, pergunta: str | None = None):
    """
    Manda o PDF ao n8n, que grava na pasta local sincronizada pelo Drive.

    O PDF vai pronto (o n8n nao refaz a inferencia): o arquivo no Drive e
    exatamente o mesmo relatorio que esta na tela, sem uma segunda chamada paga.

    Falhar aqui nao pode custar o relatorio ao usuario -- ele ja foi gerado e
    pago. Por isso devolve o erro como texto em vez de propagar, e o motivo
    tecnico vai para o stderr, nao para a tela (ver `n8n.diagnostico_visivel`).

    Returns:
        (sucesso: bool, mensagem: str).
    """
    try:
        pdf = export_pdf.relatorio_para_pdf(
            paciente_id, pergunta, resposta.modelo, resposta.relatorio
        )
        nome = n8n.enviar_relatorio(paciente_id, pergunta, resposta.modelo, pdf)
        return True, nome
    except n8n.ErroN8N as exc:
        motivo = str(exc)
    except Exception as exc:  # noqa: BLE001 - arquivamento nunca derruba a geracao
        motivo = f"Falha inesperada ao arquivar: {exc}"

    print(f"[n8n] arquivamento de {paciente_id} falhou: {motivo}", file=sys.stderr)
    return False, motivo


def avisar_se_demonstracao(chave: str) -> None:
    """
    Deixa explicito na tela quando a resposta vem do cliente simulado.

    O texto do relatorio ja vem marcado com "[SIMULADO]", mas numa apresentacao
    quem assiste ve a tela de longe: o banner evita que o conteudo de exemplo
    passe por analise real.
    """
    if chave == "demo":
        st.warning(
            "**Modo demonstração.** A resposta é um texto fixo do cliente "
            "simulado (`src/llm/demo_client.py`) — nenhum modelo é consultado, e "
            "os achados radiológicos **não** correspondem à imagem.",
            icon=":material/science:",
        )


def erro_amigavel(erro) -> str:
    """Traduz erros técnicos do provedor em orientação clara ao usuário."""
    baixo = str(erro).lower()
    if "permission_denied" in baixo or "denied access" in baixo:
        return (
            "O **projeto do Google** ligado a esta chave está bloqueado (403 "
            "`PERMISSION_DENIED`) — não é falta de cota. A chave em si pode ser "
            "válida: confira no AI Studio em qual projeto ela foi criada e se é "
            "esse o projeto com billing vinculado; se for, gere uma chave nova "
            "num projeto novo. Enquanto isso, o modelo `demo` mostra a interface "
            "com um relatório simulado."
        )
    if any(t in baixo for t in ("resource_exhausted", "quota", " 429")):
        if any(
            t in baixo
            for t in (
                "free_tier_requests",
                "perdayperprojectpermodel",
                "requests per day",
            )
        ):
            return (
                "A cota gratuita diária deste modelo foi esgotada. "
                "Selecione `gemini-flash-lite` ou aguarde a renovação da cota."
            )
        if "prepayment credits are depleted" in baixo or "insufficient_quota" in baixo:
            return (
                "A conta do provedor está sem crédito/billing ativo. "
                "Adicione crédito ou use outro provedor."
            )
        return (
            "Cota do provedor esgotada agora. O free-tier do Gemini é ~20 "
            "requisições/dia **por modelo** — troque para outro modelo no seletor "
            "(ex.: `gemini-flash-lite`), aguarde o reset diário ou habilite billing."
        )
    if any(t in baixo for t in ("503", "unavailable", "overloaded", "high demand")):
        return "Modelo temporariamente sobrecarregado (503). Tente de novo em alguns segundos."
    return f"Não consegui responder: {erro}"


def registrar_historico(pid: str, resposta) -> None:
    """Guarda a geracao no historico da sessao (desafio extra)."""
    historico = st.session_state.setdefault("historico", [])
    historico.insert(
        0,
        {
            "hora": datetime.now().strftime("%H:%M:%S"),
            "paciente": pid,
            "modelo": resposta.modelo,
            "resumo": (resposta.relatorio.resumo or "")[:120],
        },
    )
    del historico[20:]  # mantem apenas as 20 mais recentes


def _lista_md(itens, vazio: str = "—") -> str:
    itens = [str(i).strip() for i in itens if str(i).strip()]
    return "\n".join(f"- {i}" for i in itens) if itens else vazio


def renderizar_relatorio(rel, paciente_id: str, rotulo_modelo: str) -> str:
    """Formata o RelatorioClinico do LLM no layout do RF09."""
    positivos = rel.positivos()
    radiologicos = (
        ", ".join(positivos) if positivos else "nenhum achado marcado como presente"
    )
    aviso = rel.aviso or (
        "Ferramenta com finalidade exclusivamente educacional. Não constitui "
        "diagnóstico médico e não substitui a avaliação de um profissional de saúde."
    )
    return f"""#### Relatório clínico estruturado

**Caso:** `{paciente_id}` · **Modelo:** `{rotulo_modelo}`

**1. Resumo do caso**

{rel.resumo or "—"}

**2. Principais achados**

{_lista_md(rel.achados_principais)}

_Achados radiológicos (CheXpert) marcados como presentes: {radiologicos}._

**3. Hipóteses clínicas (educacionais)**

{_lista_md(rel.hipoteses)}

**4. Justificativa**

{rel.justificativa or "—"}

**5. Exames complementares sugeridos**

{_lista_md(rel.exames_sugeridos)}

> **Aviso:** {aviso}
"""


# ---------------------------------------------------------------- 5. SIDEBAR


def voltar_para_inicio():
    st.session_state.sel_paciente = None


# Sem nenhum subconjunto na máquina, o app cai em MODO DEMONSTRAÇÃO com casos
# fictícios em vez de travar numa tela de erro: os dados do Symile-MIMIC são
# credenciados e não acompanham a aplicação. O subconjunto real, se existir, tem
# precedência (ver config.subset_ativo).
if not dados.subconjunto_disponivel():
    with st.spinner("Primeiro uso: gerando casos de demonstração..."):
        try:
            demo_subset.garantir()
        except Exception as exc:  # noqa: BLE001 - sem dados não há tela; explique
            st.error(
                f"**Não consegui preparar os casos de demonstração.** {exc}",
                icon=":material/database_off:",
            )
            st.stop()
    indice_cache.clear()

INDICE = indice_cache()


# #sidebar — logo (link para o menu), seletor de paciente e aviso educacional
with st.sidebar:
    st.markdown(
        f"""
<div style="text-align:center; padding-top:0.4rem;">
  <a href="/" target="_self" title="Voltar ao menu principal">
    <img src="data:image/svg+xml;base64,{LOGO_B64}" width="84" alt="ClinicalFusion — menu principal"/>
  </a>
  <h2 style="margin:0.5rem 0 0.2rem;">ClinicalFusion</h2>
  <p style="font-size:0.8rem; opacity:0.7; margin:0;">Assistente Inteligente Multimodal para Análise Integrada de Casos Clínicos</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.divider()

    # O botao so aparece quando ha um caso aberto; limpa a selecao e volta a tela inicial
    if st.session_state.get("sel_paciente"):
        st.button(
            ":material/home: Menu principal",
            width="stretch",
            on_click=voltar_para_inicio,
        )

    # selecao == None controla qual das duas telas e renderizada abaixo
    selecao = st.selectbox(
        "Paciente",
        list(INDICE["paciente_id"]),
        index=None,
        placeholder="Selecione um caso clínico",
        format_func=lambda pid: dados.rotulo_paciente(pid, INDICE),
        key="sel_paciente",
    )

    com_rx_real = int(INDICE["cxr_real"].sum())
    st.caption(
        f"{len(INDICE)} casos do Symile-MIMIC · {com_rx_real} com radiografia real "
        f"(`patient_0001`–`patient_{com_rx_real:04d}`)"
    )

    st.divider()

    # Extra: historico de casos analisados nesta sessao.
    historico = st.session_state.get("historico", [])
    if historico:
        with st.expander(f":material/history: Histórico ({len(historico)})"):
            for item in historico:
                st.markdown(
                    f"**{item['paciente']}** · `{item['modelo']}` · {item['hora']}"
                )
                st.caption(item["resumo"] + "…" if item["resumo"] else "")
        st.divider()

    st.warning(
        "Uso **exclusivamente educacional**. Não realiza diagnóstico médico.",
        icon=":material/warning:",
    )

    # Inconfundível de propósito: quem vê a tela de longe, numa apresentação, não
    # pode achar que são casos reais do Symile-MIMIC.
    if dados.em_demonstracao():
        st.error(
            "**Modo demonstração.** Casos **fictícios**, gerados pelo próprio app. "
            "Nenhum dado do Symile-MIMIC — o dataset é de acesso credenciado e sua "
            "DUA proíbe redistribuição.",
            icon=":material/science:",
        )


# ---------------------------------------------------------------- 6. TELA INICIAL

if selecao is None:
    st.markdown(
        f"""
<div class="cf-hero">
  <img src="data:image/svg+xml;base64,{LOGO_B64}" alt="Logo ClinicalFusion"/>
  <h1>ClinicalFusion</h1>
</div>
<p class="cf-sub">Integra radiografia de tórax, ECG, exames laboratoriais e dados clínicos do paciente e gera, com um clique,
um relatório clínico estruturado com apoio de um LLM multimodal — além de um chat livre para aprofundar o
caso em linguagem natural. Finalidade exclusivamente educacional.</p>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cf-secao">As quatro modalidades do caso</div>',
        unsafe_allow_html=True,
    )
    modalidades = [
        (
            ICONES["rx"],
            "Radiografia de tórax",
            "Imagem do exame e os achados rotulados pelo CheXpert.",
        ),
        (
            ICONES["ecg"],
            "Eletrocardiograma",
            "Traçado de 12 derivações, 10 s a 500 Hz.",
        ),
        (
            ICONES["lab"],
            "Exames laboratoriais",
            "Os 50 exames mais frequentes, em valor e percentil.",
        ),
        (
            ICONES["clin"],
            "Dados clínicos",
            "Demografia e dados da admissão hospitalar.",
        ),
    ]
    cards = "".join(
        f'<div class="cf-card"><div class="icone">{icone}</div><div class="titulo">{titulo}</div><div class="texto">{texto}</div></div>'
        for icone, titulo, texto in modalidades
    )
    st.markdown(f'<div class="cf-grid4">{cards}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="cf-secao">Fluxo da aplicação</div>', unsafe_allow_html=True
    )
    passos = [
        ("Seleção do caso", "Escolha o paciente na barra lateral."),
        ("Visualização", "Radiografia, ECG, laboratório e clínica."),
        ("Integração", "Modalidades unificadas em um prompt."),
        ("Relatório", "Um clique: resumo, achados e hipóteses."),
        ("Conversa", "Chat livre com o modelo sobre o caso."),
    ]
    etapas = "".join(
        f'<div class="cf-card"><div class="cf-passo">{n}</div><div class="titulo">{titulo}</div><div class="texto">{texto}</div></div>'
        for n, (titulo, texto) in enumerate(passos, start=1)
    )
    st.markdown(f'<div class="cf-grid5">{etapas}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 7. TELA DO CASO

else:
    caso = caso_cache(selecao)
    clinicos = caso.dados_clinicos
    demo, admissao = clinicos["demografia"], clinicos["admissao"]
    laboratorio = dados.tabela_laboratorio(caso.laboratorio)
    medidos = int((~caso.laboratorio["ausente"]).sum())

    st.markdown(f"## Caso clínico — `{selecao}`")
    st.caption(
        f"`subject_id` {clinicos['subject_id']} · `hadm_id` {clinicos['hadm_id']} — "
        f"a admissão é a chave que sincroniza as quatro modalidades."
    )

    # Faixa de metricas. O Symile-MIMIC nao traz sinais vitais, entao mostramos o
    # que existe de fato: demografia, curso da internacao e cobertura dos exames.
    with st.container(border=True):
        metricas = st.columns(6)
        metricas[0].metric("Idade", dados.idade_texto(demo))
        metricas[1].metric(
            "Sexo", dados.texto(demo["sexo"]), help=dados.sexo_extenso(demo["sexo"])
        )
        metricas[2].metric("Raça/etnia", dados.texto(demo["raca"]).title())
        dias = dados.dias_internado(clinicos)
        metricas[3].metric("Internação", f"{dias} dias" if dias is not None else "—")
        metricas[4].metric("Exames medidos", f"{medidos} de 50")
        metricas[5].metric(
            "Achados no RX",
            len(dados.achados_positivos(clinicos)),
            help="Achados marcados como presentes pelo CheXpert.",
        )

    st.divider()

    (
        aba_clinica,
        aba_rx,
        aba_ecg,
        aba_lab,
        aba_chat,
        aba_relatorio,
        aba_comparar,
    ) = st.tabs(
        [
            ":material/clinical_notes: Dados clínicos",
            ":material/radiology: Radiografia",
            ":material/monitor_heart: ECG",
            ":material/science: Laboratório",
            ":material/forum: Chat",
            ":material/psychology: Relatório (LLM)",
            ":material/compare_arrows: Comparar 2 casos",
        ]
    )

    with aba_clinica:
        col_esq, col_dir = st.columns([3, 2])
        with col_esq:
            st.markdown("#### Admissão hospitalar")
            with st.container(border=True):
                st.markdown(f"**Tipo:** {admissao['tipo']}")
                st.markdown(f"**Origem:** {admissao['origem']}")
                st.markdown(f"**Desfecho:** {admissao['desfecho'] or '—'}")
                st.markdown(f"**Entrada:** {admissao['admissao_em']}")
                st.markdown(f"**Alta:** {admissao['alta_em']}")
            if admissao["obito_hospitalar"]:
                st.error("Óbito durante a internação.", icon=":material/warning:")
            st.caption(
                "As datas do MIMIC-IV são deslocadas para o futuro na desidentificação — "
                "o intervalo entre elas é real, o ano não."
            )
        with col_dir:
            st.markdown("#### Demografia")
            with st.container(border=True):
                st.markdown(f"**Idade:** {dados.idade_texto(demo)}")
                st.markdown(f"**Sexo:** {dados.sexo_extenso(demo['sexo'])}")
                st.markdown(f"**Raça/etnia:** {dados.texto(demo['raca']).title()}")
            st.info(
                "O Symile-MIMIC não traz queixa principal, história, comorbidades, "
                "medicações nem sinais vitais. O quadro clínico é inferido a partir "
                "dos exames, da radiografia e dos dados da admissão.",
                icon=":material/info:",
            )

    with aba_rx:
        col_img, col_info = st.columns([3, 2])
        with col_img:
            posicao = clinicos["radiografia"]["posicao"] or "—"
            exibir_png(
                radiografia_png(selecao),
                "Radiografia de tórax",
                f"Radiografia de tórax ({posicao})",
            )
        with col_info:
            if caso.tem_radiografia_real:
                st.success(
                    "Radiografia real do Symile-MIMIC.", icon=":material/verified:"
                )
            else:
                st.warning(
                    "Radiografia indisponível para este caso — exibindo placeholder. "
                    "Apenas os primeiros casos têm imagem real.",
                    icon=":material/image_not_supported:",
                )
            with st.container(border=True):
                st.markdown("**Achados (CheXpert)**")
                achados = dados.tabela_achados(clinicos)
                if achados.empty:
                    st.caption("Nenhum achado mencionado no laudo.")
                else:
                    st.dataframe(achados, hide_index=True, width="stretch")
            st.caption(
                "Rótulos extraídos automaticamente do laudo radiológico pelo CheXpert. "
                "Achados não mencionados no laudo não aparecem na lista."
            )

    with aba_ecg:
        st.warning(
            "**ECG sintético.** Os sinais de ECG não acompanham o material disponibilizado ",
            icon=":material/science:",
        )
        col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1])
        derivacao = col_a.selectbox("Derivação", dados.derivacoes(), index=1)
        col_b.metric("Derivações", len(dados.derivacoes()))
        col_c.metric("Duração", "10 s")
        col_d.metric("Amostragem", "500 Hz")
        exibir_png(ecg_png(selecao, derivacao), f"ECG — derivação {derivacao}")

    with aba_lab:
        extremos = dados.exames_extremos(laboratorio)
        col_a, col_b = st.columns([1, 4])
        with col_a:
            st.metric("Exames medidos", f"{medidos} de 50")
            st.metric("Percentil extremo", len(extremos))
            somente_medidos = st.toggle("Só os medidos", value=True)
        with col_b:
            tabela = (
                laboratorio[laboratorio["Situação"] != "Não medido"]
                if somente_medidos
                else laboratorio
            )
            st.dataframe(tabela, hide_index=True, width="stretch")
        st.caption(
            "O percentil situa o valor na distribuição do conjunto de treino. O MIMIC não "
            "distribui as faixas de referência dos exames, então a coluna *Situação* é "
            "estatística — não é um julgamento clínico de normalidade."
        )

    # As duas abas de LLM tem papeis separados:
    #   Chat      — dialogo livre sobre o caso, com memoria da conversa;
    #   Relatorio — um clique, saida estruturada (o prompt guia o conteudo, ver
    #               src/llm/prompt.py). Nao ha caixa de pergunta ali de proposito.
    # O resultado de ambas fica em session_state por paciente, para sobreviver
    # aos reruns do Streamlit.
    with aba_chat:
        st.markdown("#### Converse sobre o caso")
        st.caption(
            "Espaço livre para perguntar o que quiser sobre este paciente — ex.: "
            "*nos exames de sangue, o que está elevado?*, *o que a radiografia "
            "sugere?* ou *essas alterações são compatíveis entre si?* O modelo "
            "lembra das mensagens anteriores da conversa."
        )
        modelos_chat = catalogo.disponiveis(catalogo.CATALOGO)
        if not modelos_chat:
            st.warning(
                "Defina uma chave de API no `.env` para usar o chat.",
                icon=":material/key_off:",
            )
        else:
            cabec = st.columns([3, 2, 1])
            chave_chat = cabec[0].selectbox(
                "Modelo",
                [m.chave for m in modelos_chat],
                format_func=lambda c: f"{c} — {catalogo.por_chave(c).modelo}",
                key="modelo_chat",
                label_visibility="collapsed",
            )
            usar_img = cabec[1].toggle(
                "Analisar imagem",
                value=False,
                help="Envia a radiografia ao modelo (usa ~1.300 tokens a mais). "
                "Desligado, o chat usa os achados CheXpert já rotulados.",
            )
            avisar_se_demonstracao(chave_chat)
            hist_key = f"chat_hist_{selecao}"
            historico = st.session_state.setdefault(hist_key, [])
            if cabec[2].button(
                ":material/delete: Limpar", key=f"limpar_{selecao}", width="stretch"
            ):
                historico.clear()

            for msg in historico:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg.get("tokens"):
                        st.caption(msg["tokens"])

            pergunta_chat = st.chat_input("Pergunte sobre este caso...")
            if pergunta_chat:
                with st.chat_message("user"):
                    st.markdown(pergunta_chat)
                legenda = ""
                with st.chat_message("assistant"):
                    with st.spinner("Analisando o caso..."):
                        try:
                            resposta_chat, tin, tout = chat_mod.responder(
                                catalogo.por_chave(chave_chat),
                                caso,
                                list(historico),
                                pergunta_chat,
                                usar_imagem=usar_img,
                            )
                            legenda = f"tokens entrada/saída {tin or 0}/{tout or 0}"
                        except Exception as exc:  # noqa: BLE001
                            resposta_chat = erro_amigavel(exc)
                    st.markdown(resposta_chat)
                    if legenda:
                        st.caption(legenda)
                historico.append({"role": "user", "content": pergunta_chat})
                historico.append(
                    {"role": "assistant", "content": resposta_chat, "tokens": legenda}
                )

    with aba_relatorio:
        st.markdown("#### Relatório completo do caso")
        st.caption(
            "Um clique gera a análise integrada das quatro modalidades — resumo, "
            "achados, hipóteses, justificativa e exames sugeridos. Para perguntar "
            "algo específico, use a aba **Chat**."
        )

        modelos_disp = catalogo.disponiveis(catalogo.CATALOGO)
        if not modelos_disp:
            st.warning(
                "Nenhum modelo de LLM disponível. Defina `GOOGLE_API_KEY` no `.env` "
                "e recarregue a página — ou defina `CLINICALFUSION_DEMO=1` para "
                "abrir o modo demonstração, com relatório simulado.",
                icon=":material/key_off:",
            )
        else:
            col_modelo, col_botao = st.columns([3, 1])
            modelo_chave = col_modelo.selectbox(
                "Modelo",
                [m.chave for m in modelos_disp],
                format_func=lambda c: f"{c} — {catalogo.por_chave(c).modelo}",
                label_visibility="collapsed",
            )
            enviado = col_botao.button(
                ":material/psychology: Gerar relatório",
                type="primary",
                width="stretch",
                key=f"btn_gerar_{selecao}",
            )
            avisar_se_demonstracao(modelo_chave)

            if enviado:
                candidato = catalogo.por_chave(modelo_chave)
                with st.status("Processando o caso...", expanded=True) as status:
                    st.write(
                        "Integrando radiografia, ECG, laboratório e dados clínicos..."
                    )
                    st.write(
                        f"Construindo o prompt multimodal e consultando `{candidato.modelo}`..."
                    )
                    resposta = gerar_relatorio(caso, None, candidato)
                    status.update(
                        label="Relatório gerado" if resposta.ok else "Falha na geração",
                        state="complete" if resposta.ok else "error",
                        expanded=False,
                    )
                    if resposta.ok and n8n.url_webhook():
                        st.write("Arquivando o PDF na pasta sincronizada via n8n...")
                        st.session_state[f"drive_{selecao}"] = arquivar_no_drive(
                            selecao, resposta
                        )
                st.session_state[f"rel_{selecao}"] = (resposta, modelo_chave)
                st.session_state.pop(f"pac_{selecao}", None)  # limpa versao antiga
                if resposta.ok:
                    registrar_historico(selecao, resposta)

        guardado = st.session_state.get(f"rel_{selecao}")
        if guardado and not guardado[0].ok:
            st.error(erro_amigavel(guardado[0].erro), icon=":material/error:")
        elif guardado:
            resposta, chave_usada = guardado
            candidato_usado = catalogo.por_chave(chave_usada)
            rotulo = f"{resposta.provedor}/{resposta.modelo}"
            col_rel, col_evidencias = st.columns([3, 2])
            with col_rel:
                st.markdown(
                    renderizar_relatorio(resposta.relatorio, selecao, rotulo)
                )
                # RF/extra: painel de desempenho — latência, tokens e custo estimado.
                custo = candidato_usado.custo_usd(
                    resposta.tokens_entrada, resposta.tokens_saida
                )
                mcol = st.columns(3)
                mcol[0].metric("Latência", f"{resposta.latencia_s:.1f} s")
                mcol[1].metric(
                    "Tokens (ent/saí)",
                    f"{resposta.tokens_entrada or 0}/{resposta.tokens_saida or 0}",
                )
                mcol[2].metric("Custo estimado", f"US$ {custo:.4f}")

                # Resultado do arquivamento na pasta sincronizada (via n8n).
                arquivado = st.session_state.get(f"drive_{selecao}")
                if arquivado:
                    ok_drive, detalhe = arquivado
                    if ok_drive:
                        st.success(
                            f"Arquivado na pasta sincronizada: `{detalhe}`",
                            icon=":material/cloud_done:",
                        )
                    elif n8n.diagnostico_visivel():
                        # Só para quem opera a stack. Para o usuário final o
                        # arquivamento é silencioso: o relatório está na tela e o PDF
                        # é baixável, então o estado do n8n não lhe diz nada.
                        st.warning(
                            "O relatório foi gerado, mas não foi arquivado na pasta "
                            f"sincronizada. {detalhe}",
                            icon=":material/cloud_off:",
                        )

                # Extras: versão para o paciente e exportação em PDF.
                versao_pac = st.session_state.get(f"pac_{selecao}")
                b_pac, b_pdf = st.columns(2)
                if b_pac.button(
                    ":material/volunteer_activism: Explicar para o paciente",
                    key=f"btn_pac_{selecao}",
                    width="stretch",
                ):
                    with st.spinner("Traduzindo para linguagem simples..."):
                        try:
                            versao_pac = extras.explicar_para_paciente(
                                candidato_usado, resposta.relatorio
                            )
                            st.session_state[f"pac_{selecao}"] = versao_pac
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Falha ao traduzir: {exc}")

                pdf_bytes = export_pdf.relatorio_para_pdf(
                    selecao, None, resposta.modelo, resposta.relatorio,
                    versao_paciente=versao_pac,
                )
                b_pdf.download_button(
                    ":material/picture_as_pdf: Baixar PDF",
                    data=pdf_bytes,
                    file_name=f"relatorio_{selecao}.pdf",
                    mime="application/pdf",
                    width="stretch",
                )

                if versao_pac:
                    with st.container(border=True):
                        st.markdown("##### :material/volunteer_activism: Para o paciente")
                        st.write(versao_pac)
            with col_evidencias:
                # RF10: as modalidades que sustentam a resposta ficam visíveis ao lado dela.
                st.markdown("#### Exames utilizados na resposta")
                with st.expander("Radiografia de tórax", expanded=True):
                    exibir_png(radiografia_png(selecao), "Radiografia de tórax")
                with st.expander("ECG (derivação II)"):
                    exibir_png(ecg_png(selecao, "II", altura=2.4), "ECG — derivação II")
                with st.expander("Exames em percentil extremo"):
                    st.dataframe(
                        dados.exames_extremos(laboratorio),
                        hide_index=True,
                        width="stretch",
                    )
                with st.expander("Dados clínicos"):
                    st.json(
                        {"demografia": demo, "admissao": admissao},
                        expanded=False,
                    )
        else:
            st.caption(
                "O relatório estruturado aparecerá aqui depois de clicar em "
                "**Gerar relatório**."
            )

    # Extra: comparacao entre dois casos clinicos lado a lado.
    with aba_comparar:
        st.markdown("#### Compare este caso com outro")
        modelos_cmp = catalogo.disponiveis(catalogo.CATALOGO)
        if not modelos_cmp:
            st.warning(
                "Defina uma chave de API no `.env` para usar a comparação.",
                icon=":material/key_off:",
            )
        else:
            outros = [p for p in INDICE["paciente_id"] if p != selecao]
            c1, c2 = st.columns(2)
            outro = c1.selectbox(
                "Segundo caso",
                outros,
                format_func=lambda pid: dados.rotulo_paciente(pid, INDICE),
            )
            chave_cmp = c2.selectbox(
                "Modelo",
                [m.chave for m in modelos_cmp],
                format_func=lambda c: f"{c} — {catalogo.por_chave(c).modelo}",
                key="modelo_cmp",
            )
            avisar_se_demonstracao(chave_cmp)
            pergunta_cmp = st.text_input(
                "Pergunta aplicada aos dois casos",
                value="Quais são os principais achados e as hipóteses deste caso?",
            )
            if st.button(":material/compare_arrows: Comparar", type="primary"):
                candidato = catalogo.por_chave(chave_cmp)
                pares = [(selecao, caso), (outro, caso_cache(outro))]
                resultados = []
                with st.status("Gerando os dois relatórios...", expanded=False):
                    for pid, c in pares:
                        resultados.append((pid, gerar_relatorio(c, pergunta_cmp.strip(), candidato)))
                st.session_state[f"cmp_{selecao}"] = (chave_cmp, resultados)

            comparacao = st.session_state.get(f"cmp_{selecao}")
            if comparacao:
                chave_usada_cmp, resultados = comparacao
                cand_cmp = catalogo.por_chave(chave_usada_cmp)
                cols = st.columns(2)
                for coluna, (pid, resp) in zip(cols, resultados):
                    with coluna:
                        st.markdown(f"##### `{pid}`")
                        if not resp.ok:
                            st.error(erro_amigavel(resp.erro), icon=":material/error:")
                            continue
                        rel = resp.relatorio
                        exibir_png(radiografia_png(pid), f"Radiografia de {pid}")
                        st.markdown(f"**Resumo:** {rel.resumo or '—'}")
                        st.markdown("**Achados:** " + (", ".join(rel.positivos()) or "—"))
                        st.markdown("**Hipóteses:**")
                        st.markdown(_lista_md(rel.hipoteses))
                        custo = cand_cmp.custo_usd(resp.tokens_entrada, resp.tokens_saida)
                        st.caption(f"{resp.latencia_s:.1f}s · US$ {custo:.4f}")


# ---------------------------------------------------------------- 8. SCRIPT DA SIDEBAR
#
# #sidebar — o iframe (height=0, oculto via CSS) roda no documento pai e faz tres coisas:
#   1. limpa o estado salvo pelo Streamlit para a barra sempre iniciar recolhida;
#   2. recolhe a barra no primeiro carregamento;
#   3. abre (.cf-peek) quando o mouse encosta na borda esquerda e fecha ao afastar,
#      exceto se houver um popover/listbox aberto — senao o seletor fecharia junto.

components.html(
    """
<script>
const doc = window.parent.document;
if (!doc.__cfHoverInit) {
    doc.__cfHoverInit = true;
    const SELETOR = 'section[data-testid="stSidebar"]';
    try {
        const armazem = doc.defaultView.localStorage;
        Object.keys(armazem).filter(c => c.startsWith('stSidebarCollapsed')).forEach(c => armazem.removeItem(c));
    } catch (e) {}
    setTimeout(() => {
        const barra = doc.querySelector(SELETOR);
        if (barra && barra.getAttribute('aria-expanded') === 'true') {
            const botao = doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
            if (botao) botao.click();
        }
    }, 400);
    doc.addEventListener('mousemove', (e) => {
        const barra = doc.querySelector(SELETOR);
        if (!barra || barra.getAttribute('aria-expanded') !== 'false') return;
        const aberta = barra.classList.contains('cf-peek');
        if (!aberta) {
            if (e.clientX <= 24) barra.classList.add('cf-peek');
            return;
        }
        const interacaoAberta = doc.querySelector('[data-baseweb="popover"], ul[role="listbox"]');
        if (e.clientX > 344 && !interacaoAberta) barra.classList.remove('cf-peek');
    });
}
</script>
""",
    height=0,
)
