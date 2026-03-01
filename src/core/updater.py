"""
VenvStudio - Auto Update Checker
Uses raw socket + ssl — zero stdlib dependencies that PyInstaller might miss.
"""

import json
import socket
import ssl

from src.utils.constants import APP_VERSION

PYPI_HOST = "pypi.org"
PYPI_PATH = "/pypi/venvstudio/json"


def _parse_version(ver: str) -> tuple:
    try:
        return tuple(int(x) for x in ver.strip().split(".")[:4])
    except Exception:
        return (0,)


def _https_get(host: str, path: str) -> str:
    """Minimal HTTPS GET using raw socket + ssl — no http.client, no urllib."""
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: VenvStudio/{APP_VERSION}\r\n"
                f"Accept: application/json\r\n"
                f"Connection: close\r\n\r\n"
            )
            ssock.sendall(request.encode("utf-8"))
            chunks = []
            while True:
                chunk = ssock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
    raw = b"".join(chunks).decode("utf-8", errors="replace")
    # Split headers from body
    if "\r\n\r\n" in raw:
        return raw.split("\r\n\r\n", 1)[1]
    return raw


def check_for_update() -> dict:
    result = {
        "update_available": False,
        "latest_version": APP_VERSION,
        "current_version": APP_VERSION,
        "download_url": "https://pypi.org/project/venvstudio/",
        "release_url": "https://github.com/bayramkotan/VenvStudio/releases/latest",
        "error": None,
    }

    try:
        body = _https_get(PYPI_HOST, PYPI_PATH)
        data = json.loads(body)
        latest = data.get("info", {}).get("version", APP_VERSION)
        result["latest_version"] = latest
        if _parse_version(latest) > _parse_version(APP_VERSION):
            result["update_available"] = True
    except Exception as e:
        result["error"] = str(e)

    return result
