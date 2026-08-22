"""Ponto de entrada local da Huli 4 durante a Fase 0."""

from huli import __app_name__, __version__
from huli.bootstrap import build_runtime
from huli.core import InvalidKernelInput


def run_cli() -> None:
    """Executa a interface local usada para validar a fundação."""
    runtime = build_runtime()

    print(f"{__app_name__} {__version__} — Fase 0 em construção.")
    print("Kernel + Skill Registry ativos. Digite 'sair' para encerrar.")

    while True:
        try:
            text = input("Você: ")
        except (EOFError, KeyboardInterrupt):
            print("\nHuli: Encerrando interface local.")
            break

        if text.strip().lower() in {"sair", "exit", "quit"}:
            print("Huli: Encerrando interface local.")
            break

        try:
            response = runtime.kernel.process(text)
        except InvalidKernelInput as exc:
            print(f"Huli: {exc}")
            continue

        print(f"Huli: {response.text}")


def main() -> None:
    """Inicializa a interface local da Huli."""
    run_cli()


if __name__ == "__main__":
    main()
