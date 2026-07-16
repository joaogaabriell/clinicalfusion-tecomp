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
    4. RELATORIO         — placeholder ate a integracao com o LLM (Semana 3)
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

import dados

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


# ---------------------------------------------------------------- 4. RELATORIO


def montar_relatorio(pid: str, pergunta: str) -> str:
    """
    Placeholder do relatório, com a estrutura final já definida.

    As seções de conteúdo ficam vazias de propósito: quem as preenche é o LLM
    multimodal na Semana 3. O que mostramos agora são as evidências reais do
    caso, que serão o insumo do prompt — inventar resumo, achados ou hipóteses
    aqui produziria texto clínico sem nenhuma base nos dados do paciente.
    """
    caso = caso_cache(pid)
    clinicos = caso.dados_clinicos
    tabela = dados.tabela_laboratorio(caso.laboratorio)
    extremos = dados.exames_extremos(tabela)
    positivos = dados.achados_positivos(clinicos)

    demografia = clinicos["demografia"]
    perfil = (
        f"{dados.idade_texto(demografia)}, "
        f"{dados.sexo_extenso(demografia['sexo']).lower()}, "
        f"admissão por *{dados.texto(clinicos['admissao']['tipo']).lower()}*"
    )
    radiologicos = (
        ", ".join(positivos) if positivos else "nenhum achado marcado como presente"
    )
    laboratoriais = (
        "\n".join(
            f"- {linha['Exame']}: {linha['Valor']} (percentil {linha['Percentil']:.0f})"
            for _, linha in extremos.iterrows()
        )
        or "- nenhum exame em percentil extremo"
    )
    procedencia = (
        "radiografia real"
        if caso.tem_radiografia_real
        else "radiografia mock (placeholder)"
    )

    return f"""
#### Relatório clínico estruturado

**Pergunta:** _{pergunta}_

> :material/build: **Aguardando a integração com o LLM multimodal (Semana 3).**
> As seções abaixo já refletem a estrutura definida no RF09. Por ora, exibimos as
> **evidências reais** que comporão o prompt multimodal — nenhum texto clínico é
> gerado nesta etapa.

**Evidências disponíveis para o prompt**

- **Perfil:** {perfil}
- **Exames laboratoriais medidos:** {int((~caso.laboratorio["ausente"]).sum())} de 50
- **Achados radiológicos (CheXpert):** {radiologicos}
- **Modalidades:** {procedencia}, ECG mock, laboratório real, dados clínicos reais

**Exames em percentil extremo**

{laboratoriais}

---

**1. Resumo do caso** · **2. Principais achados** · **3. Hipóteses clínicas (educacionais)** ·
**4. Justificativa** · **5. Exames complementares sugeridos**

_Seções a serem preenchidas pelo LLM multimodal._

> **Aviso:** ferramenta com finalidade **exclusivamente educacional**. **Não constitui
> diagnóstico médico** e **não substitui a avaliação de um profissional de saúde**.
"""


# ---------------------------------------------------------------- 5. SIDEBAR


def voltar_para_inicio():
    st.session_state.sel_paciente = None


# O app depende do subconjunto gerado localmente a partir dos dados credenciados;
# sem ele nao ha caso nenhum para mostrar.
if not dados.subconjunto_disponivel():
    st.error(
        "**Subconjunto não encontrado.** Os dados do Symile-MIMIC são de acesso credenciado "
        "e não acompanham o repositório.",
        icon=":material/database_off:",
    )
    st.markdown(
        """
Para gerar o subconjunto na sua máquina:

```bash
cp .env.example .env        # e ajuste SYMILE_MIMIC_DIR
python -m src.build_subset --n-casos 150
```

Detalhes em [`data/README.md`](../data/README.md).
"""
    )
    st.stop()

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
    st.warning(
        "Uso **exclusivamente educacional**. Não realiza diagnóstico médico.",
        icon=":material/warning:",
    )


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
            st.image(
                caso.radiografia,
                caption=f"Radiografia de tórax ({posicao})",
                width="stretch",
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
            "**ECG sintético.** Os sinais de ECG não acompanham o material disponibilizado "
            "(`ecg_*.npy` ausentes). O traçado abaixo é gerado e serve para validar o fluxo "
            "da aplicação; o formato é idêntico ao do dado real.",
            icon=":material/science:",
        )
        col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1])
        derivacao = col_a.selectbox("Derivação", dados.derivacoes(), index=1)
        col_b.metric("Derivações", len(dados.derivacoes()))
        col_c.metric("Duração", "10 s")
        col_d.metric("Amostragem", "500 Hz")
        st.pyplot(figura_ecg(selecao, derivacao))

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
                    st.write(
                        "Integrando radiografia, ECG, laboratório e dados clínicos..."
                    )
                    time.sleep(0.6)
                    st.write("Construindo o prompt multimodal...")
                    time.sleep(0.6)
                    st.write("Consultando o LLM multimodal...")
                    time.sleep(0.8)
                    status.update(
                        label="Relatório gerado", state="complete", expanded=False
                    )
                st.session_state[f"rel_{selecao}"] = montar_relatorio(
                    selecao, pergunta.strip()
                )

        relatorio = st.session_state.get(f"rel_{selecao}")
        if relatorio:
            col_rel, col_evidencias = st.columns([3, 2])
            with col_rel:
                st.markdown(relatorio)
            with col_evidencias:
                # RF10: as modalidades que sustentam a resposta ficam visíveis ao lado dela.
                st.markdown("#### Exames utilizados na resposta")
                with st.expander("Radiografia de tórax", expanded=True):
                    st.image(caso.radiografia, width="stretch")
                with st.expander("ECG (derivação II)"):
                    st.pyplot(figura_ecg(selecao, "II", altura=2.4))
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
                "O relatório estruturado aparecerá aqui após o envio de uma pergunta."
            )


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
