"""ClinicalFusion — interface do assistente multimodal para analise de casos clinicos.

Estrutura do arquivo:
    1. CONFIGURACAO      — page_config, logo e icones SVG
    2. ESTILOS           — CSS global (cards, grids e comportamento da sidebar)
    3. DADOS E FIGURAS   — cache das modalidades e geracao do grafico do ECG
    4. RELATORIO         — montagem do texto estruturado
    5. SIDEBAR           — logo, selecao do paciente e aviso educacional
    6. TELA INICIAL      — hero, modalidades e fluxo (quando nenhum caso esta selecionado)
    7. TELA DO CASO      — metricas + abas (clinica, RX, ECG, laboratorio, relatorio)
    8. SCRIPT DA SIDEBAR — JS que abre a barra lateral ao aproximar o mouse da borda
"""

import base64
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, str(Path(__file__).parent))

from mock_data import PACIENTES, gerar_ecg, gerar_radiografia, rotulo_paciente, tabela_laboratorio

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
def radiografia_cache(pid: str):
    cfg = PACIENTES[pid]["xray"]
    return gerar_radiografia(cfg["seed"], cfg["cardiomegalia"], cfg["consolidacao"])


@st.cache_data
def ecg_cache(pid: str):
    cfg = PACIENTES[pid]["ecg"]
    irregular = "irregular" in cfg["ritmo"].lower() or "fibrila" in cfg["ritmo"].lower()
    return gerar_ecg(cfg["seed"], cfg["fc"], irregular)


def figura_ecg(pid: str, altura: float = 3.2):
    """Traçado do ECG sobre o papel milimetrado (0,04 s por quadradinho menor)."""
    t, sinal = ecg_cache(pid)
    fig, ax = plt.subplots(figsize=(11, altura))
    ax.set_facecolor("#fff7f7")
    ax.xaxis.set_major_locator(MultipleLocator(0.2))
    ax.xaxis.set_minor_locator(MultipleLocator(0.04))
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(MultipleLocator(0.1))
    ax.grid(which="major", color="#f1a5a5", linewidth=0.7)
    ax.grid(which="minor", color="#fadcdc", linewidth=0.4)
    ax.plot(t, sinal, color="#1a1a1a", linewidth=0.9)
    ax.set_xlim(0, t[-1])
    ax.set_ylim(-0.9, 1.6)
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("mV")
    ax.set_title("Derivação II — 10 s", fontsize=10, loc="left")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- 4. RELATORIO


def montar_relatorio(pid: str, pergunta: str) -> str:
    r = PACIENTES[pid]["relatorio"]
    achados = "\n".join(f"- {a}" for a in r["achados"])
    hipoteses = "\n".join(f"- {h}" for h in r["hipoteses"])
    exames = "\n".join(f"- {e}" for e in r["exames_sugeridos"])
    return f"""
#### Relatório clínico estruturado

**Pergunta:** _{pergunta}_

**1. Resumo do caso**

{r["resumo"]}

**2. Principais achados**

{achados}

**3. Hipóteses clínicas (educacionais)**

{hipoteses}

**4. Justificativa baseada nas evidências**

{r["justificativa"]}

**5. Exames complementares sugeridos**

{exames}

> **Aviso:** conteúdo gerado com finalidade **exclusivamente educacional**. Este relatório **não constitui
> diagnóstico médico** e **não substitui a avaliação de um profissional de saúde**.
"""


# ---------------------------------------------------------------- 5. SIDEBAR


def voltar_para_inicio():
    st.session_state.sel_paciente = None


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
        st.button(":material/home: Menu principal", width="stretch", on_click=voltar_para_inicio)

    # selecao == None controla qual das duas telas e renderizada abaixo
    selecao = st.selectbox(
        "Paciente",
        list(PACIENTES),
        index=None,
        placeholder="Selecione um caso clínico",
        format_func=rotulo_paciente,
        key="sel_paciente",
    )

    st.divider()
    st.warning("Uso **exclusivamente educacional**. Não realiza diagnóstico médico.", icon=":material/warning:")


# ---------------------------------------------------------------- 6. TELA INICIAL

if selecao is None:
    st.markdown(
        f"""
<div class="cf-hero">
  <img src="data:image/svg+xml;base64,{LOGO_B64}" alt="Logo ClinicalFusion"/>
  <h1>ClinicalFusion</h1>
</div>
<p class="cf-sub">Integra radiografia de tórax, ECG, exames laboratoriais e dados clínicos do paciente e, a partir de uma
pergunta em linguagem natural, gera um relatório clínico estruturado com apoio de um LLM multimodal —
finalidade exclusivamente educacional.</p>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cf-secao">As quatro modalidades do caso</div>', unsafe_allow_html=True)
    modalidades = [
        (ICONES["rx"], "Radiografia de tórax", "Imagem do exame integrada à visão do caso."),
        (ICONES["ecg"], "Eletrocardiograma", "Traçado do sinal com frequência e ritmo."),
        (ICONES["lab"], "Exames laboratoriais", "Resultados com referências e alterações."),
        (ICONES["clin"], "Dados clínicos", "Demografia, queixa, história e medicações."),
    ]
    cards = "".join(
        f'<div class="cf-card"><div class="icone">{icone}</div><div class="titulo">{titulo}</div><div class="texto">{texto}</div></div>'
        for icone, titulo, texto in modalidades
    )
    st.markdown(f'<div class="cf-grid4">{cards}</div>', unsafe_allow_html=True)

    st.markdown('<div class="cf-secao">Fluxo da aplicação</div>', unsafe_allow_html=True)
    passos = [
        ("Seleção do caso", "Escolha o paciente na barra lateral."),
        ("Visualização", "Radiografia, ECG, laboratório e clínica."),
        ("Pergunta", "Questione o caso em linguagem natural."),
        ("Integração", "Modalidades unificadas em um prompt."),
        ("Relatório", "Resumo, achados e hipóteses."),
    ]
    etapas = "".join(
        f'<div class="cf-card"><div class="cf-passo">{n}</div><div class="titulo">{titulo}</div><div class="texto">{texto}</div></div>'
        for n, (titulo, texto) in enumerate(passos, start=1)
    )
    st.markdown(f'<div class="cf-grid5">{etapas}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 7. TELA DO CASO

else:
    p = PACIENTES[selecao]
    demo, vitais = p["demografia"], p["sinais_vitais"]

    st.markdown(f"## Caso clínico — `{selecao}`")
    st.caption(f"Admissão: {demo['admissao']}")

    # Faixa de metricas: idade, sexo e os cinco sinais vitais
    with st.container(border=True):
        metricas = st.columns(7)
        metricas[0].metric("Idade", f"{demo['idade']} anos")
        metricas[1].metric("Sexo", demo["sexo"][0], help=demo["sexo"])
        for coluna, (nome, valor) in zip(metricas[2:], vitais.items()):
            coluna.metric(nome, valor)

    st.divider()

    aba_clinica, aba_rx, aba_ecg, aba_lab, aba_relatorio = st.tabs(
        [
            ":material/clinical_notes: Dados clínicos",
            ":material/radiology: Radiografia",
            ":material/monitor_heart: ECG",
            ":material/science: Laboratório",
            ":material/psychology: Relatório (LLM)",
        ]
    )

    with aba_clinica:
        col_esq, col_dir = st.columns([3, 2])
        with col_esq:
            st.markdown("#### Queixa principal")
            st.info(p["clinica"]["queixa_principal"])
            st.markdown("#### História clínica")
            st.write(p["clinica"]["historia"])
        with col_dir:
            with st.container(border=True):
                st.markdown("**Comorbidades**")
                for item in p["clinica"]["comorbidades"]:
                    st.markdown(f"- {item}")
            with st.container(border=True):
                st.markdown("**Medicações em uso**")
                for item in p["clinica"]["medicacoes"]:
                    st.markdown(f"- {item}")
            with st.container(border=True):
                st.markdown("**Alergias**")
                st.write(p["clinica"]["alergias"])
            st.caption(f"Altura: {demo['altura_cm']} cm · Peso: {demo['peso_kg']} kg")

    with aba_rx:
        col_img, col_info = st.columns([3, 2])
        with col_img:
            st.image(radiografia_cache(selecao), caption="Radiografia de tórax (PA)", width="stretch")
        with col_info:
            with st.container(border=True):
                st.markdown("**Impressão radiológica**")
                st.write(p["xray"]["impressao"])

    with aba_ecg:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Frequência cardíaca", f"{p['ecg']['fc']} bpm")
        col_b.metric("Ritmo", p["ecg"]["ritmo"])
        col_c.metric("Duração exibida", "10 s")
        st.pyplot(figura_ecg(selecao))
        st.caption(f"Observação: {p['ecg']['obs']}")

    with aba_lab:
        df = tabela_laboratorio(selecao)
        alterados = int((df["Alteração"] != "Normal").sum())
        col_a, col_b = st.columns([1, 4])
        col_a.metric("Exames alterados", f"{alterados} de {len(df)}")
        with col_b:
            st.dataframe(df, hide_index=True, width="stretch")

    # Aba do relatorio: pergunta em linguagem natural -> etapas de processamento -> texto estruturado.
    # O resultado fica em session_state por paciente para sobreviver aos reruns do Streamlit.
    with aba_relatorio:
        st.markdown("#### Pergunte sobre o caso em linguagem natural")
        with st.form(key=f"form_{selecao}", border=False):
            pergunta = st.text_area(
                "Pergunta",
                placeholder="Ex.: Quais são os principais achados deste caso? As alterações laboratoriais são compatíveis com a radiografia?",
                label_visibility="collapsed",
            )
            enviado = st.form_submit_button("Gerar relatório", type="primary")

        if enviado:
            if not pergunta.strip():
                st.error("Digite uma pergunta antes de gerar o relatório.")
            else:
                with st.status("Processando o caso...", expanded=True) as status:
                    st.write("Lendo as quatro modalidades do paciente...")
                    time.sleep(0.6)
                    st.write("Integrando radiografia, ECG, laboratório e dados clínicos...")
                    time.sleep(0.6)
                    st.write("Construindo o prompt multimodal...")
                    time.sleep(0.6)
                    st.write("Consultando o LLM multimodal...")
                    time.sleep(0.8)
                    status.update(label="Relatório gerado", state="complete", expanded=False)
                st.session_state[f"rel_{selecao}"] = montar_relatorio(selecao, pergunta.strip())

        relatorio = st.session_state.get(f"rel_{selecao}")
        if relatorio:
            col_rel, col_evidencias = st.columns([3, 2])
            with col_rel:
                st.markdown(relatorio)
            with col_evidencias:
                st.markdown("#### Exames utilizados na resposta")
                with st.expander("Radiografia de tórax", expanded=True):
                    st.image(radiografia_cache(selecao), width="stretch")
                with st.expander("ECG"):
                    st.pyplot(figura_ecg(selecao, altura=2.4))
                with st.expander("Exames laboratoriais alterados"):
                    df = tabela_laboratorio(selecao)
                    st.dataframe(df[df["Alteração"] != "Normal"], hide_index=True, width="stretch")
        else:
            st.caption("O relatório estruturado aparecerá aqui após o envio de uma pergunta.")


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
