"""
Testes do subconjunto de demonstracao.

O ponto central e o contrato com `src.loaders`, que tem de ler os casos ficticios
sem distingui-los dos reais. Se ele quebrar, o modo demonstracao para de abrir.
"""

import json

import pytest

from src import config, demo_subset, loaders


@pytest.fixture
def demo(tmp_path):
    """Um subconjunto de demonstracao pequeno, gerado fora do repositorio."""
    destino = tmp_path / "demo"
    demo_subset.construir(3, destino=destino)
    return destino


def test_indice_tem_as_mesmas_colunas_do_subconjunto_real(demo):
    indice = loaders.listar_pacientes(demo)

    assert list(indice.columns) == [
        "paciente_id",
        "subject_id",
        "hadm_id",
        "idade",
        "sexo",
        "cxr_real",
        "ecg_real",
        "labs_presentes",
    ]
    assert len(indice) == 3


def test_loaders_le_o_caso_ficticio_pelo_contrato_real(demo):
    caso = loaders.carregar_caso("demo_0001", demo)

    assert caso.paciente_id == "demo_0001"
    assert caso.radiografia.size == (config.CXR_LADO, config.CXR_LADO)
    assert list(caso.ecg.columns) == ["tempo_s"] + config.ECG_DERIVACOES
    assert len(caso.ecg) == config.ECG_N_AMOSTRAS
    # Os 50 exames sempre presentes como linha, ausentes inclusive.
    assert len(caso.laboratorio) == len(config.LABS)
    assert set(caso.laboratorio.columns) == {
        "itemid",
        "exame",
        "valor",
        "percentil",
        "ausente",
    }


def test_nenhuma_modalidade_se_apresenta_como_real(demo):
    """
    Vale para a proveniencia (que a interface exibe) e para o indice, que alimenta
    os rotulos "real/mock" das modalidades.
    """
    caso = loaders.carregar_caso("demo_0002", demo)

    for modalidade in ("dados_clinicos", "laboratorio", "radiografia", "ecg"):
        assert caso.proveniencia[modalidade] == "mock"
    assert caso.tem_radiografia_real is False
    assert caso.proveniencia["fonte"].startswith("DEMONSTRACAO")

    indice = loaders.listar_pacientes(demo)
    assert not indice["cxr_real"].any()
    assert not indice["ecg_real"].any()


def test_casos_sao_reproduziveis(tmp_path):
    """Mesmo paciente, geracoes diferentes, caso identico."""
    primeira = tmp_path / "a"
    segunda = tmp_path / "b"
    demo_subset.construir(2, destino=primeira)
    demo_subset.construir(2, destino=segunda)

    for pid in ("demo_0001", "demo_0002"):
        assert loaders.carregar_dados_clinicos(pid, primeira) == (
            loaders.carregar_dados_clinicos(pid, segunda)
        )


def test_pacientes_diferentes_geram_casos_diferentes(demo):
    a = loaders.carregar_dados_clinicos("demo_0001", demo)
    b = loaders.carregar_dados_clinicos("demo_0002", demo)

    assert a["subject_id"] != b["subject_id"]
    assert a != b


def test_identificadores_nao_colidem_com_a_faixa_do_mimic(demo):
    """Ids em 9xxxxxxx, fora da faixa do MIMIC: nao podem ser cruzados com ela."""
    for pid in ("demo_0001", "demo_0002", "demo_0003"):
        clinico = loaders.carregar_dados_clinicos(pid, demo)
        assert 90_000_000 <= clinico["subject_id"] < 100_000_000
        assert 90_000_000 <= clinico["hadm_id"] < 100_000_000


def test_clinical_data_json_e_legivel_e_marcado(demo):
    bruto = (demo / "demo_0001" / "clinical_data.json").read_text(encoding="utf-8")
    clinico = json.loads(bruto)

    assert "MODO DEMONSTRACAO" in clinico["_proveniencia"]["aviso"]
    assert clinico["admissao"]["obito_hospitalar"] is False


def test_garantir_gera_uma_vez_e_reaproveita(tmp_path):
    destino = tmp_path / "demo"
    assert not demo_subset.disponivel(destino)

    demo_subset.garantir(2, destino=destino)
    assert demo_subset.disponivel(destino)
    marca = (destino / "index.csv").stat().st_mtime_ns

    # A segunda chamada nao deve regerar nada: custa segundos.
    demo_subset.garantir(2, destino=destino)
    assert (destino / "index.csv").stat().st_mtime_ns == marca


def test_n_casos_invalido_falha_alto(tmp_path):
    with pytest.raises(ValueError, match="n_casos"):
        demo_subset.construir(0, destino=tmp_path / "demo")


def test_subset_ativo_prefere_o_real(tmp_path, monkeypatch):
    """
    O modo demonstracao e rede de seguranca para quem nao tem os dados, e nunca
    pode mascarar o subconjunto real de quem tem.
    """
    real = tmp_path / "symile-mimic"
    demo = tmp_path / "demo"
    monkeypatch.setattr(config, "SUBSET_DIR", real)
    monkeypatch.setattr(config, "DEMO_DIR", demo)

    assert config.subset_ativo() is None
    assert config.em_demonstracao() is False

    demo_subset.construir(1, destino=demo)
    assert config.subset_ativo() == demo
    assert config.em_demonstracao() is True

    real.mkdir(parents=True)
    (real / config.ARQUIVO_INDICE).write_text("paciente_id\n", encoding="utf-8")
    assert config.subset_ativo() == real
    assert config.em_demonstracao() is False
