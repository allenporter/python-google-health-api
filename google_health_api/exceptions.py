"""Exceptions for Google Health API calls."""

from .model.operation import Status


class GoogleHealthApiError(Exception):
    """Error talking to the Google Health API."""


class HealthApiException(GoogleHealthApiError):
    """Raised during generic problems talking to the API."""


class HealthAuthException(GoogleHealthApiError):
    """Raised due to authentication problems talking to the API (401 / unauthenticated)."""


class HealthApiForbiddenException(GoogleHealthApiError):
    """Raised due to permission/forbidden errors talking to the API (403)."""


class HealthApiServiceDisabledException(HealthApiForbiddenException):
    """Raised when the Google Health API is not enabled in the Google Cloud Project."""


class HealthApiScopeInsufficientException(HealthApiForbiddenException):
    """Raised when the OAuth token lacks required permissions/scopes."""


class HealthApiRateLimitException(HealthApiException):
    """Raised when API quotas or rate limits are exceeded (429)."""


class HealthApiNotFoundException(HealthApiException):
    """Raised when a requested resource was not found (404)."""


class HealthApiConnectionException(HealthApiException):
    """Raised when network or connection errors occur talking to the API."""


class HealthApiAccountNotLinkedException(HealthApiException):
    """Raised when the user account is not linked to Google Health / Fitbit."""


class OperationError(GoogleHealthApiError):
    """Raised when a long-running operation completes with an error status.

    Attributes:
        status: The error status from the completed operation, containing
            the error code, message, and optional details.
    """

    def __init__(self, status: Status) -> None:
        """Initialize the operation error.

        Args:
            status: The Status object from the failed operation.
        """
        self.status = status
        super().__init__(f"Operation failed: {status.message} (code={status.code})")


class WebhookSignatureError(GoogleHealthApiError):
    """Raised when a webhook payload signature is invalid or cannot be verified."""
