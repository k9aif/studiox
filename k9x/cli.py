# SPDX-License-Identifier: Apache-2.0
"""Command-line interface for the K9-AIF Studio."""

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 12999

STATE_DIR = Path.home() / ".k9x"
PID_FILE = STATE_DIR / "studio.pid"
LOG_FILE = STATE_DIR / "studio.log"

BUNDLED_GENERATOR_TEMPLATES = Path(__file__).resolve().parent / "_generator_templates"

DEFAULT_TEST_PROMPT = "Who is Elon Musk? Answer in one paragraph."

CONTAINER_HELP = f"""\
Running k9x studio in a container
==================================

Dockerfile:

    FROM python:3.11-slim
    RUN pip install --no-cache-dir k9x
    EXPOSE {DEFAULT_PORT}
    ENV K9X_STUDIO_USER=demo \\
        K9X_STUDIO_PASSWORD=demo
    CMD ["k9x", "studio", "--host", "0.0.0.0", "--port", "{DEFAULT_PORT}"]

Build and run:

    docker build -t k9x-studio .
    k9x config                       # writes ./.env-example — edit and save as .env
    docker run -p {DEFAULT_PORT}:{DEFAULT_PORT} --env-file .env k9x-studio

Then open http://localhost:{DEFAULT_PORT} on the host.
Set K9X_STUDIO_USER / K9X_STUDIO_PASSWORD in .env to restrict access
(defaults to demo/demo).
"""


def _display_host(host: str) -> str:
    return "localhost" if host in ("0.0.0.0", "::") else host


def _port_in_use(host: str, port: int) -> bool:
    probe_host = _display_host(host)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((probe_host, port)) == 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="k9x",
        description="K9-AIF Studio — visual architecture builder for K9-AIF projects.",
        epilog=(
            "Examples:\n"
            "  k9x studio                 Start the studio (foreground, like 'ollama serve')\n"
            "  k9x studio --bg            Start the studio in the background\n"
            "  k9x studio --stop          Stop a background studio\n"
            f"  k9x studio --port 9000     Use a different port (default port: {DEFAULT_PORT})\n"
            "  k9x config                 Write ./.env-example with LLM provider settings\n"
            "  k9x test-llm               Send a test prompt to the LLM configured in .env\n"
            "  k9x help container         Show how to run the studio in a container\n"
            "\n"
            "'--bg' / '--background' may also be given before the subcommand:\n"
            "  k9x --bg studio\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    help_p = sub.add_parser("help", help="Show this help message")
    help_p.add_argument(
        "topic", nargs="?", choices=["container"], default=None,
        help="show help on a specific topic ('container')",
    )

    studio = sub.add_parser("studio", help="Start the K9-AIF Studio")
    studio.add_argument(
        "--host", default=os.environ.get("K9X_STUDIO_HOST", DEFAULT_HOST),
        help=f"bind host (default: {DEFAULT_HOST})",
    )
    studio.add_argument(
        "--port", type=int, default=int(os.environ.get("K9X_STUDIO_PORT", DEFAULT_PORT)),
        help=f"bind port (default: {DEFAULT_PORT}, env K9X_STUDIO_PORT)",
    )
    studio.add_argument(
        "--no-browser", action="store_true",
        help="don't open a browser tab automatically",
    )
    studio.add_argument(
        "--bg", "--background", dest="bg", action="store_true",
        help="run the studio in the background and return immediately",
    )
    studio.add_argument(
        "--stop", action="store_true",
        help="stop a studio previously started with --bg",
    )

    config = sub.add_parser("config", help="Write a starter .env file with LLM provider settings")
    config.add_argument(
        "--output", default=".env-example",
        help="output path (default: ./.env-example)",
    )
    config.add_argument(
        "--force", action="store_true",
        help="overwrite the output file if it already exists",
    )

    test_llm = sub.add_parser("test-llm", help="Send a test prompt to the LLM configured in .env")
    test_llm.add_argument(
        "--prompt", default=DEFAULT_TEST_PROMPT,
        help="prompt to send (default: a short 'who is...' question, answered in one paragraph)",
    )

    return parser


def _prepare_env() -> None:
    """Load ./.env (if present) and point scaffold export at bundled templates."""
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    if BUNDLED_GENERATOR_TEMPLATES.is_dir():
        os.environ.setdefault("K9X_GENERATOR_TEMPLATES_DIR", str(BUNDLED_GENERATOR_TEMPLATES))


def _run_foreground(host: str, port: int, no_browser: bool) -> int:
    if _port_in_use(host, port):
        print(f"[k9x] Port {port} is already in use — is k9x studio already running?")
        print(f"[k9x]   Try 'k9x studio --port <other-port>', or 'k9x studio --stop' "
              f"if it was started with --bg.")
        return 1

    _prepare_env()

    url = f"http://{_display_host(host)}:{port}"
    print("[k9x] K9-AIF Studio")
    print(f"[k9x] Listening on {_display_host(host)}:{port}")
    print(f"[k9x] URL: {url}")
    print("[k9x] Press Ctrl+C to stop.")
    print("[k9x] Ready to rumble!")

    if not no_browser:
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    import uvicorn
    import backend.main as backend_main
    uvicorn.run(backend_main.app, host=host, port=port, log_level="info")
    return 0


def _start_background(host: str, port: int, no_browser: bool) -> int:
    url = f"http://{_display_host(host)}:{port}"

    if _port_in_use(host, port):
        print(f"[k9x] k9x studio already appears to be running at {url} "
              f"(port {port} is in use) — nothing to do.")
        return 0

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "k9x", "studio",
        "--host", host, "--port", str(port), "--no-browser",
    ]
    with open(LOG_FILE, "ab") as log_f:
        proc = subprocess.Popen(
            cmd, stdout=log_f, stderr=log_f, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    PID_FILE.write_text(str(proc.pid))

    print(f"[k9x] K9-AIF Studio")
    print(f"[k9x] Listening on {_display_host(host)}:{port} (pid {proc.pid})")
    print(f"[k9x] URL: {url}")
    print(f"[k9x]   logs: {LOG_FILE}")
    print(f"[k9x]   stop: k9x studio --stop")
    print("[k9x] Ready to rumble!")

    if not no_browser:
        time.sleep(1.0)
        webbrowser.open(url)
    return 0


def _stop_background() -> int:
    if not PID_FILE.exists():
        print("[k9x] No background k9x studio process found.")
        return 0

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"[k9x] Stopped k9x studio (pid {pid}).")
    except ProcessLookupError:
        print(f"[k9x] k9x studio (pid {pid}) was not running.")
    finally:
        PID_FILE.unlink(missing_ok=True)
    return 0


def _cmd_studio(args) -> int:
    if args.stop:
        return _stop_background()
    if args.bg:
        return _start_background(args.host, args.port, args.no_browser)
    return _run_foreground(args.host, args.port, args.no_browser)


def _cmd_config(args) -> int:
    from k9x.env_template import ENV_EXAMPLE_CONTENT

    output = Path(args.output)
    if output.exists() and not args.force:
        print(f"[k9x] {output} already exists — use --force to overwrite.")
        return 1

    output.write_text(ENV_EXAMPLE_CONTENT)
    print(f"[k9x] Wrote {output}")
    print(f"[k9x] Edit it, then run: cp {output} .env && k9x studio")
    return 0


def _cmd_test_llm(args) -> int:
    _prepare_env()

    provider = os.environ.get("LLM_PROVIDER", "ollama").strip()
    endpoint = os.environ.get("LLM_ENDPOINT", "").strip().rstrip("/")
    model    = os.environ.get("LLM_MODEL", "").strip() or "granite3-dense:2b"
    api_key  = os.environ.get("LLM_API_KEY", "").strip()

    if not endpoint:
        print("[k9x] No LLM_ENDPOINT set.")
        print("[k9x] Run 'k9x config' to write a starter .env, edit it, then re-run this command.")
        return 1

    if not endpoint.startswith(("http://", "https://")):
        endpoint = "http://" + endpoint

    print(f"[k9x] Provider: {provider}")
    print(f"[k9x] Endpoint: {endpoint}")
    print(f"[k9x] Model:    {model}")
    print(f"[k9x] Prompt:   {args.prompt}")
    print("[k9x] Sending test prompt...")

    from backend.api.routes import _call_llm
    try:
        response = _call_llm(endpoint, provider, model, api_key, args.prompt)
    except Exception as exc:
        print(f"[k9x] ✕ LLM call failed: {exc}")
        return 1

    print()
    print(response.strip())
    print()
    print("[k9x] ✓ LLM responded successfully.")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)

    # 'k9x --help container' / 'k9x -h container' — argparse's built-in -h/--help
    # action exits before a trailing positional like "container" is ever seen, so
    # handle this combo directly. 'k9x help container' (subcommand) also works,
    # see below.
    if len(argv) >= 2 and argv[0] in ("--help", "-h") and argv[1] == "container":
        print(CONTAINER_HELP)
        return 0

    # Allow '--bg'/'--background' before the subcommand too: 'k9x --bg studio'
    leading_bg = False
    for flag in ("--bg", "--background"):
        while flag in argv:
            argv.remove(flag)
            leading_bg = True

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "help"):
        if args.command == "help" and getattr(args, "topic", None) == "container":
            print(CONTAINER_HELP)
        else:
            parser.print_help()
        return 0

    if args.command == "studio":
        if leading_bg:
            args.bg = True
        return _cmd_studio(args)

    if args.command == "config":
        return _cmd_config(args)

    if args.command == "test-llm":
        return _cmd_test_llm(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
