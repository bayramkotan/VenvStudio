"""
VenvStudio - Auto Update Checker
Checks PyPI for new versions and notifies the user.
"""

import json
import http.client
import ssl
from packaging import version as pkg_version

from src.utils.constants import APP_VERSION

PYPI_HOST = "pypi.org"
PYPI_PATH = "/pypi/venvstudio/json"


def check_for_update() -> dict:
    """
    Check PyPI for a newer version of VenvStudio.
    Uses http.client directly to avoid email module dependency in PyInstaller builds.
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

        try:
            if pkg_version.parse(latest) > pkg_version.parse(APP_VERSION):
                result["update_available"] = True
        except Exception:
            if latest != APP_VERSION:
                result["update_available"] = True

    except Exception as e:
        result["error"] = str(e)

    return result
