# 02 — Organização das Modalidades de Dados

> **Objetivo do item:** apresentar como os dados do subconjunto escolhido foram organizados e como cada modalidade é associada ao mesmo paciente.

---

## 1. Quantidade de casos selecionados

> _A preencher pela equipe._ Número de casos (entre 100 e 500) e critério de seleção.

## 2. Estrutura de pastas

Estrutura adotada (uma pasta por paciente):

```
data/symile-mimic/
├── patient_0001/
│   ├── chest_xray.png       # radiografia de tórax
│   ├── ecg.csv              # ECG
│   ├── laboratory.csv       # exames laboratoriais
│   └── clinical_data.json   # dados demográficos e clínicos
├── patient_0002/
│   └── ...
```

## 3. Localização de cada modalidade

| Modalidade | Arquivo | Observações |
|------------|---------|-------------|
| Radiografia de tórax | `patient_XXXX/chest_xray.png` | > _A preencher_ |
| ECG | `patient_XXXX/ecg.csv` | > _A preencher_ |
| Exames laboratoriais | `patient_XXXX/laboratory.csv` | > _A preencher_ |
| Dados clínicos | `patient_XXXX/clinical_data.json` | > _A preencher_ |

## 4. Schema de cada arquivo

> _A preencher pela equipe._ Definir colunas/campos de `laboratory.csv`, `ecg.csv` e as chaves de `clinical_data.json`.

## 5. Associação das modalidades ao mesmo paciente

> _A preencher pela equipe._ O identificador `patient_XXXX` (derivado do ID de paciente/admissão do MIMIC) é a chave que unifica todas as modalidades.

---

> ⚠️ Lembrete: os dados reais **não vão para o GitHub** (DUA). Ver [`../data/README.md`](../data/README.md).
