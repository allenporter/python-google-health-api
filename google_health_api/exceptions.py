"""Exceptions for Google Health API calls."""


class GoogleHealthApiError(Exception):
    """Error talking to the Google Health API."""


class HealthApiException(GoogleHealthApiError):
    """Raised during generic problems talking to the API."""


class HealthAuthException(GoogleHealthApiError):
    """Raised due to authentication problems talking to the API."""


class HealthApiForbiddenException(GoogleHealthApiError):
    """Raised due to permission/forbidden errors talking to the API."""


class WebhookSignatureError(GoogleHealthApiError):
    """Raised when a webhook payload signature is invalid or cannot be verified."""
