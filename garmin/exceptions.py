"""Custom exceptions for Garmin Connect integration."""

class GarminException(Exception):
    """Base exception for all Garmin operations."""
    pass

class GarminAuthError(GarminException):
    """Raised when authentication with Garmin Connect fails."""
    pass

class GarminDataFetchError(GarminException):
    """Raised when data fetching from Garmin endpoints fails."""
    pass
