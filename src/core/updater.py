"""
VenvStudio - Auto Update Checker
Checks PyPI for new versions and notifies the user.
"""

import json
import http.client
import ssl

from src.utils.constants import APP_VERSION

PYPI_HOST = "pypi.org"
PYPI_PATH = "/pypi/venvstudio/json"


def _parse_version(ver_str: str) -> tuple:
    """Parse version string to comparable tuple. e.g. '1.3.23' → (1, 3, 23)"""
    try:
        return tuple(int(x) for x in ver_str.strip().split(".")[:4])
    except Exception:
        return (0,)


def check_for_update() -> dict:
    """
    Check PyPI for a newer version of VenvStudio.
    Uses http.client directly to avoid email/packaging module issues in PyInstaller builds.
    """
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
        conn = http.client.HTTPSConnection(PYPI_HOST, timeout=10, context=ctx)
        conn.request("GET", PYPI_PATH, headers={
            "Accept": "application/json",
            "User-Agent": f"VenvStudio/{APP_VERSION}",
        })
        resp = conn.getresponse()
        if resp.status != 200:
            result["error"] = f"HTTP {resp.status}"
            return result

        data = json.loads(resp.read().decode("utf-8"))
        conn.close()

        latest = data.get("info", {}).get("version", APP_VERSION)
        result["latest_version"] = latest

        if _parse_version(latest) > _parse_version(APP_VERSION):
            result["update_available"] = True

    except Exception as e:
        result["error"] = str(e)

    return result
