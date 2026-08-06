"""
Abre o navegador na aplicacao assim que ela comeca a responder.

Chamado em segundo plano por `iniciar.sh` / `iniciar.bat`.

O Streamlit abriria o navegador sozinho, mas fora do modo headless ele antes faz
uma pergunta no terminal ("Welcome to Streamlit! Email:") e fica parado
esperando um Enter -- o app nunca sobe, e quem deu duplo clique no lancador nao
tem como saber o motivo. Subimos em headless e abrimos o navegador aqui.

Esperar a porta responder evita a tela de erro de conexao do navegador.

Uso:
    python abrir_navegador.py [porta]
"""

import socket
import sys
import time
import webbrowser

PORTA_PADRAO = 8501
ESPERA_MAXIMA_S = 90.0
INTERVALO_S = 0.5


def esperar_porta(porta: int, limite_s: float = ESPERA_MAXIMA_S) -> bool:
    """Se a porta comecou a aceitar conexao dentro do limite."""
    prazo = time.monotonic() + limite_s
    while time.monotonic() < prazo:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonda:
            sonda.settimeout(1.0)
            if sonda.connect_ex(("127.0.0.1", porta)) == 0:
                return True
        time.sleep(INTERVALO_S)
    return False


def main() -> int:
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else PORTA_PADRAO
    url = f"http://localhost:{porta}"

    if not esperar_porta(porta):
        # Nao e fatal: o lancador ja imprimiu a URL e o Streamlit segue rodando.
        print(f"[abrir_navegador] o app nao respondeu em {ESPERA_MAXIMA_S:.0f}s; abra {url} manualmente.")
        return 1

    webbrowser.open(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
