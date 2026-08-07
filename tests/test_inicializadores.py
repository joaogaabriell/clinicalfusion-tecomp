from pathlib import Path

import abrir_navegador


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


def test_abrir_url_usa_navegador_do_windows_no_wsl(monkeypatch):
    chamadas = []
    monkeypatch.setattr(abrir_navegador, "release", lambda: "microsoft-standard-WSL2")
    monkeypatch.setattr(
        abrir_navegador.subprocess,
        "run",
        lambda comando, **opcoes: chamadas.append((comando, opcoes)),
    )

    assert abrir_navegador.abrir_url("http://localhost:8501") is True
    assert chamadas[0][0] == [
        "cmd.exe",
        "/c",
        "start",
        "",
        "http://localhost:8501",
    ]
    assert chamadas[0][1]["check"] is True


def test_abrir_url_usa_webbrowser_fora_do_wsl(monkeypatch):
    monkeypatch.setattr(abrir_navegador, "release", lambda: "6.8.0-linux")
    monkeypatch.setattr(
        abrir_navegador.webbrowser,
        "open",
        lambda url: url.endswith("8501"),
    )

    assert abrir_navegador.abrir_url("http://localhost:8501") is True
