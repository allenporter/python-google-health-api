"""
.. include:: ../README.md
"""

from . import api, auth, client, const, exceptions, model
from .api import GoogleHealthApi

__all__ = [
    "GoogleHealthApi",
    "api",
    "auth",
    "client",
    "const",
    "exceptions",
    "model",
]
