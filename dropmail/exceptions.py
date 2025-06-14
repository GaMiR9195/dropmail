class DropMailError(Exception):
    """Base exception for DropMail"""
    pass

class SessionExpiredError(DropMailError):
    """Raised when session has expired"""
    pass

class NetworkError(DropMailError):
    """Raised when network request fails"""
    pass