"""Start the local 4GMC preview or a Shopify-connected tunnel session."""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent


def settings() -> dict[str, str]:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        raise ValueError("Missing .env. Copy .env.example to .env and fill in the private settings.")
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def configured(values: dict[str, str], key: str) -> bool:
    value = os.environ.get(key, values.get(key, "")).strip()
    return bool(value and not value.startswith("change-this") and value != "generate-a-fernet-key")


def https_origin(value: str) -> str:
    value = value.strip().rstrip("/")
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.path
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Enter only the public HTTPS address, such as https://your-tunnel.example.")
    if parts.hostname in {"localhost", "127.0.0.1"}:
        raise ValueError("For this launcher, use a public HTTPS tunnel or domain for Shopify callbacks.")
    return value


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
            return response.status == 200 and b"<title>4GMC" in response.read(65536)
    except (OSError, urllib.error.URLError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4GMC on this computer.")
    parser.add_argument("--shopify", action="store_true", help="Use a public HTTPS tunnel to connect a live Shopify store.")
    parser.add_argument("--url", help="Public HTTPS tunnel or domain, for example https://example.ngrok-free.app.")
    parser.add_argument("--port", type=int, default=8000, help="Local port (default: 8000).")
    parser.add_argument("--check", action="store_true", help="Validate the setup without starting the server.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically.")
    args = parser.parse_args()

    if sys.version_info < (3, 11):
        raise ValueError("Python 3.11 or newer is required.")
    if not 1 <= args.port <= 65535:
        raise ValueError("The port must be between 1 and 65535.")
    values = settings()
    missing = [key for key in ("ADMIN_PASSWORD", "SESSION_SECRET", "TOKEN_ENCRYPTION_KEY") if not configured(values, key)]
    if missing:
        raise ValueError("Set these values in .env before starting: " + ", ".join(missing))

    shopify_mode = args.shopify or bool(args.url)
    if not shopify_mode and not args.check and len(sys.argv) == 1 and sys.stdin.isatty():
        print("4GMC local launcher")
        print("  1. Local preview")
        print("  2. Live Shopify store (requires an HTTPS tunnel)")
        shopify_mode = input("Choose 1 or 2 [1]: ").strip() == "2"

    local_url = f"http://127.0.0.1:{args.port}"
    if shopify_mode:
        tunnel_url = args.url or os.environ.get("PUBLIC_URL", values.get("PUBLIC_URL", ""))
        if not tunnel_url.startswith("https://") and not args.check and sys.stdin.isatty():
            tunnel_url = input("Public HTTPS tunnel URL: ").strip()
        public_url = https_origin(tunnel_url)
        print(f"Local server: {local_url}")
        print(f"Open this address for Shopify testing: {public_url}")
        print(f"Set the Shopify app URL to: {public_url}")
        print(f"Allow this Shopify redirect URL: {public_url}/api/shopify/callback")
        print(f"Your HTTPS tunnel must forward to {local_url}.")
    else:
        public_url = f"http://localhost:{args.port}"
        print(f"Local preview: {public_url}")
        print("For a live Shopify connection, choose option 2 and use an HTTPS tunnel.")

    if args.check:
        print("Configuration check passed. No server was started.")
        return 0
    if not port_available(args.port):
        if not shopify_mode and ready(args.port):
            print(f"4GMC is already running at {public_url}. Opening the existing preview.", flush=True)
            if not args.no_browser:
                webbrowser.open(public_url)
            return 0
        if shopify_mode and ready(args.port):
            raise ValueError(
                f"4GMC is already running on port {args.port}. Stop that preview before starting Shopify tunnel mode."
            )
        raise ValueError(f"Port {args.port} is used by another program. Close it or use --port {args.port + 1}.")

    environment = os.environ.copy()
    environment["PUBLIC_URL"] = public_url
    command = [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(args.port)]
    print("Starting 4GMC. Press Ctrl+C here to stop it.", flush=True)
    process = subprocess.Popen(command, cwd=ROOT, env=environment)
    try:
        for _ in range(80):
            if process.poll() is not None:
                return process.returncode or 1
            if ready(args.port):
                if not args.no_browser:
                    webbrowser.open(public_url)
                break
            time.sleep(0.25)
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as error:
        print(f"Setup needed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
