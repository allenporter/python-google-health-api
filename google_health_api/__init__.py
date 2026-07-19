"""
.. include:: ../README.md
"""

from .api import GoogleHealthApi
from . import api, auth, client, const, exceptions, model, webhook

__all__ = [
    "GoogleHealthApi",
    "api",
    "auth",
    "client",
    "const",
    "exceptions",
    "model",
    "webhook",
]
