from __future__ import annotations

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


def init_app(app: Flask) -> None:
    """
    Apply ProxyFix if configured.
    """
    if app.config.get("USE_PROXYFIX", True):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
