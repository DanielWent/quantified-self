class GarminSyncError(Exception):
    """Base exception for Garmin sync operations."""
    pass

class DriveSyncError(Exception):
    """Exception for Google Drive sync operations."""
    pass
