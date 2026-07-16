"""ClinicalFusion — prototipo inicial da interface (Semana 1, dados ficticios)."""

import base64
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, str(Path(__file__).parent))

from mock_data import PACIENTES, gerar_ecg, gerar_radiografia, rotulo_paciente, tabela_laboratorio

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title="ClinicalFusion",
    page_icon=str(ASSETS / "favicon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

LOGO_B64 = base64.b64encode((ASSETS / "logo.svg").read_bytes()).decode()

st.markdown(
    """
<style>
.block-container { max-width: 1180px; }
.cf-grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem; }
.cf-grid5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.8rem; margin-bottom: 1.2rem; }
@media (max-width: 800px) { .cf-grid4, .cf-grid5 { grid-template-columns: repeat(2, 1fr); } }
.cf-card { border: 1px solid rgba(128, 128, 128, 0.35); border-radius: 12px; padding: 1.1rem 0.9rem; text-align: center; }
.cf-card .icone { font-size: 2.1rem; line-height: 1.2; }
.cf-card .titulo { font-weight: 600; margin: 0.5rem 0 0.3rem; }
.cf-card .texto { font-size: 0.85rem; opacity: 0.75; }
.cf-passo { width: 28px; height: 28px; border-radius: 50%; background: #0ea5e9; color: #fff; font-weight: 700;
            display: flex; align-items: center; justify-content: center; margin: 0 auto; }
</style>
""",
    unsafe_allow_html=True,
)


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
    ax.set_title("Derivação II — 10 s (sinal sintético)", fontsize=10, loc="left")
    fig.tight_layout()
    return fig


def montar_relatorio(pid: str, pergunta: str) -> str:
    r = PACIENTES[pid]["relatorio"]
    achados = "\n".join(f"- {a}" for a in r["achados"])
    hipoteses = "\n".join(f"- {h}" for h in r["hipoteses"])
    exames = "\n".join(f"- {e}" for e in r["exames_sugeridos"])
    return f"""
#### 📄 Relatório clínico estruturado

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

> ⚠️ **Aviso:** conteúdo gerado com finalidade **exclusivamente educacional**. Este relatório **não constitui
> diagnóstico médico** e **não substitui a avaliação de um profissional de saúde**.

🔌 _Resposta simulada (placeholder). A integração real com o LLM multimodal está prevista para a Semana 3._
"""


def voltar_para_inicio():
    st.session_state.sel_paciente = None


with st.sidebar:
    st.markdown(
        f"""
<div style="text-align:center; padding-top:0.4rem;">
  <img src="data:image/svg+xml;base64,{LOGO_B64}" width="84"/>
  <h2 style="margin:0.5rem 0 0.2rem;">ClinicalFusion</h2>
  <p style="font-size:0.8rem; opacity:0.7; margin:0;">Assistente Inteligente Multimodal para Análise Integrada de Casos Clínicos</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.divider()

    st.button("🏠 Voltar à tela inicial", width="stretch", on_click=voltar_para_inicio)
    selecao = st.selectbox(
        "Paciente",
        list(PACIENTES),
        index=None,
        placeholder="Selecione um caso clínico",
        format_func=rotulo_paciente,
        key="sel_paciente",
    )

    st.divider()
    st.warning("Uso **exclusivamente educacional**. Não realiza diagnóstico médico.", icon="⚠️")
    st.caption("Protótipo — Semana 1 · dados fictícios (mock). O subconjunto do Symile-MIMIC será integrado nas próximas semanas.")


if selecao is None:
    st.markdown(
        f"""
<div style="text-align:center; padding:0.4rem 0 0.8rem;">
  <img src="data:image/svg+xml;base64,{LOGO_B64}" width="96"/>
  <h1 style="margin:0.6rem 0 0.3rem;">ClinicalFusion</h1>
  <p style="opacity:0.8; margin:0;">Análise integrada de casos clínicos com LLMs multimodais · protótipo da interface (Semana 1)</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.info(
        "O ClinicalFusion reúne quatro modalidades de dados de um mesmo paciente e as envia, junto com a pergunta do "
        "usuário, a um LLM multimodal que gera um relatório clínico estruturado — com finalidade exclusivamente educacional.",
        icon="🧬",
    )

    st.markdown("<h3 style='text-align:center; margin-top:1.2rem;'>As quatro modalidades do caso</h3>", unsafe_allow_html=True)
    modalidades = [
        ("🩻", "Radiografia de tórax", "Imagem do exame integrada à visão do caso."),
        ("📈", "Eletrocardiograma", "Traçado do sinal com frequência e ritmo."),
        ("🧪", "Exames laboratoriais", "Resultados com referências e alterações."),
        ("📋", "Dados clínicos", "Demografia, queixa, história e medicações."),
    ]
    cards = "".join(
        f'<div class="cf-card"><div class="icone">{icone}</div><div class="titulo">{titulo}</div><div class="texto">{texto}</div></div>'
        for icone, titulo, texto in modalidades
    )
    st.markdown(f'<div class="cf-grid4">{cards}</div>', unsafe_allow_html=True)

    st.markdown("<h3 style='text-align:center; margin-top:1.2rem;'>Fluxo da aplicação</h3>", unsafe_allow_html=True)
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

else:
    p = PACIENTES[selecao]
    demo, vitais = p["demografia"], p["sinais_vitais"]

    st.markdown(f"## 🩺 Caso clínico — `{selecao}`")
    st.caption(f"Admissão: {demo['admissao']} · dados fictícios para demonstração")

    with st.container(border=True):
        metricas = st.columns(7)
        metricas[0].metric("Idade", f"{demo['idade']} anos")
        metricas[1].metric("Sexo", demo["sexo"][0], help=demo["sexo"])
        for coluna, (nome, valor) in zip(metricas[2:], vitais.items()):
            coluna.metric(nome, valor)

    st.divider()

    aba_clinica, aba_rx, aba_ecg, aba_lab, aba_relatorio = st.tabs(
        ["📋 Dados clínicos", "🩻 Radiografia", "📈 ECG", "🧪 Laboratório", "🤖 Relatório (LLM)"]
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
            st.image(radiografia_cache(selecao), caption="Radiografia de tórax (PA) — imagem sintética de demonstração", width="stretch")
        with col_info:
            with st.container(border=True):
                st.markdown("**Impressão (mock)**")
                st.write(p["xray"]["impressao"])
            st.caption("Na Semana 2 esta área exibirá a radiografia real do caso (arquivo `chest_xray.png` do subconjunto).")

    with aba_ecg:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Frequência cardíaca", f"{p['ecg']['fc']} bpm")
        col_b.metric("Ritmo", p["ecg"]["ritmo"])
        col_c.metric("Duração exibida", "10 s")
        st.pyplot(figura_ecg(selecao))
        st.caption(f"Observação (mock): {p['ecg']['obs']}")

    with aba_lab:
        df = tabela_laboratorio(selecao)
        alterados = int((df["Alteração"] != "Normal").sum())
        col_a, col_b = st.columns([1, 4])
        col_a.metric("Exames alterados", f"{alterados} de {len(df)}")
        with col_b:
            st.dataframe(df, hide_index=True, width="stretch")
        st.caption("Valores fictícios. Na Semana 2 os resultados virão do arquivo `laboratory.csv` de cada paciente.")

    with aba_relatorio:
        st.markdown("#### Pergunte sobre o caso em linguagem natural")
        with st.form(key=f"form_{selecao}", border=False):
            pergunta = st.text_area(
                "Pergunta",
                placeholder="Ex.: Quais são os principais achados deste caso? As alterações laboratoriais são compatíveis com a radiografia?",
                label_visibility="collapsed",
            )
            enviado = st.form_submit_button("🧠 Gerar relatório", type="primary")

        if enviado:
            if not pergunta.strip():
                st.error("Digite uma pergunta antes de gerar o relatório.")
            else:
                with st.status("Processando o caso...", expanded=True) as status:
                    st.write("📥 Lendo as quatro modalidades do paciente...")
                    time.sleep(0.6)
                    st.write("🔗 Integrando radiografia, ECG, laboratório e dados clínicos...")
                    time.sleep(0.6)
                    st.write("📝 Construindo o prompt multimodal...")
                    time.sleep(0.6)
                    st.write("🤖 Consultando o LLM multimodal (simulado)...")
                    time.sleep(0.8)
                    status.update(label="Relatório gerado", state="complete", expanded=False)
                st.session_state[f"rel_{selecao}"] = montar_relatorio(selecao, pergunta.strip())

        relatorio = st.session_state.get(f"rel_{selecao}")
        if relatorio:
            col_rel, col_evidencias = st.columns([3, 2])
            with col_rel:
                st.markdown(relatorio)
            with col_evidencias:
                st.markdown("#### 🔎 Exames utilizados na resposta")
                with st.expander("🩻 Radiografia de tórax", expanded=True):
                    st.image(radiografia_cache(selecao), width="stretch")
                with st.expander("📈 ECG"):
                    st.pyplot(figura_ecg(selecao, altura=2.4))
                with st.expander("🧪 Exames laboratoriais alterados"):
                    df = tabela_laboratorio(selecao)
                    st.dataframe(df[df["Alteração"] != "Normal"], hide_index=True, width="stretch")
        else:
            st.caption("O relatório estruturado aparecerá aqui após o envio de uma pergunta.")
