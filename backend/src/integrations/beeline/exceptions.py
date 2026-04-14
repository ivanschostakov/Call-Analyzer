from typing import Any


class BeelineIntegrationError(RuntimeError):
    """Base exception for the Beeline integration."""


class BeelineConfigurationError(BeelineIntegrationError):
    """Raised when the Beeline client is missing required configuration."""


class BeelineTransportError(BeelineIntegrationError):
    """Raised when the Beeline API cannot be reached."""

    def __init__(self, message: str, *, method: str, path: str) -> None:
        super().__init__(message)
        self.method = method
        self.path = path


class BeelineApiError(BeelineIntegrationError):
    """Raised when the Beeline API returns an error response."""

    def __init__(self, message: str, *, status_code: int, method: str, path: str, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.path = path
        self.details = details


class BeelineResponseFormatError(BeelineIntegrationError):
    """Raised when the Beeline API returns an unexpected payload shape."""

