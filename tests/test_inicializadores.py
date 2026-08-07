from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


def test_inicializador_linux_repara_venv_sem_pip():
    script = (RAIZ / "iniciar.sh").read_text(encoding="utf-8")

    assert '"$VENV_PY" -m pip --version' in script
    assert '"$VENV_PY" -m ensurepip --upgrade' in script
    assert 'PACOTE_VENV="python${VERSAO_PY}-venv"' in script
    assert 'VENV=".venv-linux"' in script
    assert 'VENV=".venv-macos"' in script
    assert 'CACHE_CLINICALFUSION="${XDG_CACHE_HOME:-$HOME/.cache}/clinicalfusion"' in script


def test_inicializador_windows_repara_venv_sem_pip():
    script = (RAIZ / "iniciar.bat").read_text(encoding="utf-8")

    assert '"%VENV_PY%" -m pip --version' in script
    assert '"%VENV_PY%" -m ensurepip --upgrade' in script
