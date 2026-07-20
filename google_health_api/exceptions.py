"""Exceptions for Google Health API calls."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model.operation import Status


class GoogleHealthApiError(Exception):
    """Error talking to the Google Health API."""


class HealthApiException(GoogleHealthApiError):
    """Raised during generic problems talking to the API."""


class HealthAuthException(GoogleHealthApiError):
    """Raised due to authentication problems talking to the API."""


class HealthApiForbiddenException(GoogleHealthApiError):
    """Raised due to permission/forbidden errors talking to the API."""


class OperationError(GoogleHealthApiError):
    """Raised when a long-running operation completes with an error status.

    Attributes:
        status: The error status from the completed operation, containing
            the error code, message, and optional details.
    """

    def __init__(self, status: "Status") -> None:
        """Initialize the operation error.

        Args:
            status: The Status object from the failed operation.
        """
        self.status = status
        super().__init__(f"Operation failed: {status.message} (code={status.code})")


class WebhookSignatureError(GoogleHealthApiError):
    """Raised when a webhook payload signature is invalid or cannot be verified."""
