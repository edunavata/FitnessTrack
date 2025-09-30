"""WSGI proxy middleware configuration helper."""

from __future__ import annotations

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


def init_app(app: Flask) -> None:
    """Apply :class:`werkzeug.middleware.proxy_fix.ProxyFix` when enabled.

    Parameters
    ----------
    app: flask.Flask
        Application whose WSGI pipeline should respect upstream proxy headers.

    Notes
    -----
    Controlled by the ``USE_PROXYFIX`` configuration flag (defaults to
    ``True``). ``ProxyFix`` trusts a single hop for ``X-Forwarded-*`` headers.
    """
    if app.config.get("USE_PROXYFIX", True):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
