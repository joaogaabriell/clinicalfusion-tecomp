# Dados — ClinicalFusion

> 🔒 **Nenhum dado real é versionado neste repositório.** O Symile-MIMIC é de acesso **credenciado** e sua *Data Use Agreement (DUA)* **proíbe redistribuição**. Os dados reais ficam **apenas na máquina local** e são bloqueados pelo `.gitignore`.

---

## 📁 Organização das modalidades (estrutura esperada)

Cada caso clínico é uma pasta de paciente contendo as quatro modalidades, associadas pelo mesmo identificador:

```
data/symile-mimic/               # (local, ignorado pelo Git)
├── patient_0001/
│   ├── chest_xray.png           # radiografia de tórax
│   ├── ecg.csv                  # eletrocardiograma (sinal)
│   ├── laboratory.csv           # exames laboratoriais
│   └── clinical_data.json       # dados demográficos e clínicos
├── patient_0002/
│   └── ...
└── ...                          # entre 100 e 500 casos
```

O identificador da pasta (`patient_XXXX`) é a **chave que relaciona todas as modalidades** de um mesmo paciente.

### Conteúdo esperado de cada arquivo

| Arquivo | Conteúdo | Formato |
|---------|----------|---------|
| `chest_xray.png` | Imagem da radiografia de tórax | PNG/JPG |
| `ecg.csv` | Amostras do sinal de ECG (12 derivações) | CSV |
| `laboratory.csv` | Exames laboratoriais (exame, valor, unidade, referência) | CSV |
| `clinical_data.json` | Idade, sexo, queixa, sinais vitais, comorbidades | JSON |

> A definição final do schema de cada arquivo é responsabilidade da equipe de implementação (ver `docs/02-organizacao-modalidades.md`).

---

## ⬇️ Como obter os dados reais (acesso credenciado)

O download **não pode ser feito por este repositório** nem automatizado sem credenciais. Cada integrante que for manipular os dados precisa:

1. Ter uma conta no **PhysioNet** com **credenciamento aprovado**.
2. Concluir o treinamento **CITI** ("Data or Specimens Only Research").
3. Assinar a **DUA** na página do dataset: <https://physionet.org/content/symile-mimic/1.0.0/>

Com o credenciamento aprovado, baixar via terminal (substitua `SEU_USUARIO`):

```bash
wget -r -N -c -np --user SEU_USUARIO --ask-password \
  https://physionet.org/files/symile-mimic/1.0.0/
```

Em seguida, mover/organizar o subconjunto escolhido (100–500 casos) para `data/symile-mimic/` seguindo a estrutura acima.

---

## 🧪 Dados de exemplo

Se a equipe precisar de exemplos versionáveis para desenvolvimento da interface, use **dados fictícios claramente sintéticos** em `data/sample_patients/` (marcados como MOCK), **nunca** derivados dos dados reais credenciados.
