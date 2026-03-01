"""
VenvStudio - Auto Update Checker
Checks PyPI using only http.client — no urllib, no email, no packaging.
Works reliably in PyInstaller builds.
"""

import http.client
import json
import ssl

from src.utils.constants import APP_VERSION

PYPI_HOST = "pypi.org"
PYPI_PATH = "/pypi/venvstudio/json"


def _parse_version(ver: str) -> tuple:
    """'1.3.25' -> (1, 3, 25)"""
    try:
        return tuple(int(x) for x in ver.strip().split(".")[:4])
    except Exception:
        return (0,)


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
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(PYPI_HOST, context=ctx, timeout=10)
        conn.request(
            "GET", PYPI_PATH,
            headers={
                "Accept": "application/json",
                "User-Agent": f"VenvStudio/{APP_VERSION}",
                "Host": PYPI_HOST,
            }
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        conn.close()

        latest = data.get("info", {}).get("version", APP_VERSION)
        result["latest_version"] = latest

        if _parse_version(latest) > _parse_version(APP_VERSION):
            result["update_available"] = True

    except Exception as e:
        result["error"] = str(e)

    return result
