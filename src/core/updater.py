"""
VenvStudio Updater
Checks PyPI for newer versions using only stdlib (urllib).
No external dependencies — works in PyInstaller builds.
"""

import json
import ssl
import urllib.request
from src.utils.constants import APP_VERSION

PYPI_URL = "https://pypi.org/pypi/venvstudio/json"


def _parse_version(ver_str: str) -> tuple:
    """Parse version string to comparable tuple. e.g. '1.3.24' → (1, 3, 24)"""
    try:
        return tuple(int(x) for x in ver_str.strip().split(".")[:4])
    except Exception:
        return (0,)


def check_for_update() -> dict:
    """
    Check PyPI for a newer version.
    Returns dict with keys:
      - update_available (bool)
      - latest (str)
      - current (str)
      - error (str or None)
    """
    result = {
        "update_available": False,
        "latest": APP_VERSION,
        "current": APP_VERSION,
        "error": None,
    }

    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            PYPI_URL,
            headers={
                "User-Agent": f"VenvStudio/{APP_VERSION}",
                "Accept": "application/json",
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest = data.get("info", {}).get("version", APP_VERSION)
        result["latest"] = latest

        if _parse_version(latest) > _parse_version(APP_VERSION):
            result["update_available"] = True

    except Exception as e:
        result["error"] = str(e)

    return result
