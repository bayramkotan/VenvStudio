"""
VenvStudio - Auto Update Checker
Checks PyPI for new versions and notifies the user.
"""

import json
import urllib.request
import urllib.error
from packaging import version as pkg_version

from src.utils.constants import APP_VERSION

PYPI_URL = "https://pypi.org/pypi/venvstudio/json"


def check_for_update() -> dict:
    """
    Check PyPI for a newer version of VenvStudio.

    Returns:
        dict with keys:
            - update_available (bool)
            - latest_version (str)
            - current_version (str)
            - download_url (str)
            - error (str or None)
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
        req = urllib.request.Request(
            PYPI_URL,
            headers={"Accept": "application/json", "User-Agent": f"VenvStudio/{APP_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest = data.get("info", {}).get("version", APP_VERSION)
        result["latest_version"] = latest

        try:
            if pkg_version.parse(latest) > pkg_version.parse(APP_VERSION):
                result["update_available"] = True
        except Exception:
            # Fallback: simple string comparison
            if latest != APP_VERSION:
                result["update_available"] = True

    except urllib.error.URLError as e:
        result["error"] = f"Network error: {e.reason}"
    except Exception as e:
        result["error"] = str(e)

    return result
