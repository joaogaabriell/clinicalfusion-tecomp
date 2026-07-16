# Dados — ClinicalFusion

> 🔒 **Nenhum dado real é versionado neste repositório.** O Symile-MIMIC é de acesso **credenciado** e sua *Data Use Agreement (DUA)* **proíbe redistribuição**. O subconjunto gerado fica **apenas na máquina local** e é bloqueado pelo `.gitignore`.

---

## ⚠️ O material disponibilizado está incompleto

A pasta do Symile-MIMIC que recebemos **não traz todas as modalidades em formato bruto**. O que existe de fato:

| Arquivo | Situação |
|---------|----------|
| `symile_mimic_data.csv` | ✅ Completo — $11.622$ admissões, com demografia e os 14 achados do CheXpert |
| `train.csv` / `val.csv` / `test.csv` | ✅ Completos — exames laboratoriais (valores e percentis) |
| `labs_means.json` | ✅ Completo — médias de percentil dos 50 exames |
| `code/` | ✅ Scripts originais de geração do dataset |
| `symile_mimic_model.ckpt` | ✅ Íntegro ($738\,\mathrm{MB}$) — checkpoint do modelo treinado |
| `data_npy/test/cxr_test.npy` | ⚠️ **Truncado** — o cabeçalho declara $4.640$ imagens ($\approx 5{,}7\,\mathrm{GB}$), mas o arquivo tem $57\,\mathrm{MB}$: só **46 imagens** estão íntegras |
| `data_npy/*/ecg_*.npy` | ❌ **Ausentes** — nenhum sinal de ECG foi disponibilizado |
| `data_npy/train/cxr_train.npy`, `data_npy/val/cxr_val.npy` | ❌ **Ausentes** |

As colunas `cxr_path` e `ecg_path` dos CSVs apontam para o **MIMIC-CXR-JPG** e o **MIMIC-IV-ECG** completos, que são datasets à parte e **não** foram disponibilizados.

> Consequência para o projeto: **exames laboratoriais e dados clínicos são reais**; a **radiografia é real em 46 casos** e mock nos demais; o **ECG é sempre mock**. Ver [`../docs/01-estudo-dataset-symile-mimic.md`](../docs/01-estudo-dataset-symile-mimic.md).

---

## 📁 Estrutura gerada

O subconjunto segue o formato uma-pasta-por-paciente pedido no enunciado:

```
data/symile-mimic/               # (local, ignorado pelo Git)
├── index.csv                    # índice dos casos + procedência de cada modalidade
├── patient_0001/
│   ├── chest_xray.png           # radiografia de tórax (320x320)
│   ├── ecg.csv                  # ECG, 12 derivações x 5000 amostras
│   ├── laboratory.csv           # 50 exames laboratoriais
│   └── clinical_data.json       # demografia, admissão, achados e procedência
├── patient_0002/
└── ...                          # 150 casos por padrão
```

O identificador `patient_XXXX` é a **chave que relaciona as quatro modalidades**. Ele deriva da admissão (`hadm_id`) do MIMIC-IV, que é a chave real do dataset — todos os `subject_id`/`hadm_id` originais ficam registrados no `clinical_data.json` e no `index.csv`.

### Schema de cada arquivo

| Arquivo | Colunas / chaves | Procedência |
|---------|------------------|-------------|
| `chest_xray.png` | Imagem RGB $320 \times 320$ | **real** nos 46 primeiros casos; placeholder nos demais |
| `ecg.csv` | `tempo_s`, `I`, `II`, `III`, `aVR`, `aVL`, `aVF`, `V1`–`V6` — $5000$ linhas @ $500\,\mathrm{Hz}$, valores em $[-1, 1]$ | **mock** (sinal sintético) |
| `laboratory.csv` | `itemid`, `exame`, `valor`, `percentil`, `ausente` — sempre as mesmas 50 linhas | **real** |
| `clinical_data.json` | `demografia`, `admissao`, `radiografia.achados_chexpert`, `_proveniencia` | **real** |

Os 50 exames aparecem **sempre**, inclusive os não medidos (`ausente = True`, `valor` vazio). A ausência de um exame é informação clínica e não some da tabela — é assim que o dataset original trata o assunto, com um vetor de indicadores de ausência.

### Procedência é explícita

Todo `clinical_data.json` traz um bloco `_proveniencia` dizendo, modalidade a modalidade, se o dado é `real` ou `mock`, e por quê:

```json
"_proveniencia": {
  "fonte": "Symile-MIMIC 1.0.0 (PhysioNet, acesso credenciado)",
  "dados_clinicos": "real",
  "laboratorio": "real",
  "radiografia": "real",
  "ecg": "mock",
  "motivo_mock": "..."
}
```

O `index.csv` traz as colunas `cxr_real` e `ecg_real` para filtrar rapidamente os casos com radiografia verdadeira.

> 🩺 **Sobre o mock.** O ECG sintético respeita o formato real (12 derivações, $5000$ amostras, $[-1, 1]$) para que o código de leitura e de plotagem seja **o mesmo** dos dados reais — trocar o mock por dado verdadeiro depois não muda nenhuma assinatura. Já a radiografia ausente é um **cartão de aviso legível**, e não uma imagem médica sintética: em contexto clínico, uma imagem falsa realista poderia ser confundida com um exame de verdade.

---

## ⚙️ Como gerar o subconjunto

**1. Apontar para os dados credenciados** (a pasta `1.0.0` do Symile-MIMIC):

```bash
cp .env.example .env
# edite .env e ajuste SYMILE_MIMIC_DIR
```

**2. Gerar:**

```bash
source .venv/bin/activate
python -m src.build_subset --n-casos 150 --limpar
```

O enunciado pede entre $100$ e $500$ casos; o script recusa valores fora dessa faixa. A geração leva cerca de $13\,\mathrm{s}$ e ocupa $\approx 79\,\mathrm{MB}$.

---

## ⬇️ Como obter os dados reais (acesso credenciado)

O download **não pode ser automatizado por este repositório**. Cada integrante que for manipular os dados precisa:

1. Ter uma conta no **PhysioNet** com **credenciamento aprovado**.
2. Concluir o treinamento **CITI** ("Data or Specimens Only Research").
3. Assinar a **DUA** na página do dataset: <https://physionet.org/content/symile-mimic/1.0.0/>

Com o credenciamento aprovado:

```bash
wget -r -N -c -np --user SEU_USUARIO --ask-password \
  https://physionet.org/files/symile-mimic/1.0.0/
```

> 📌 **Pendência com a professora.** Os arquivos `ecg_train/val/test.npy`, `cxr_train.npy`, `cxr_val.npy` e a versão íntegra de `cxr_test.npy` constam do `SHA256SUMS.txt` mas **não vieram**. Sem eles, o **RF05** (exibir o ECG do paciente) não tem como usar sinal real.
