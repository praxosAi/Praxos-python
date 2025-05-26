# my_api_sdk/exceptions.py
class APIError(Exception):
    """Custom exception for API errors."""
    def __init__(self, status_code: int, message: str, response_data: dict = None, **kwargs):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data or {}
        super().__init__(f"API Error {status_code}: {message}")

    def __str__(self):
        return f"APIError(status_code={self.status_code}, message='{self.message}', details={self.response_data})"
    
class APIKeyInvalidError(APIError):
    """Exception raised when the API token/key is invalid."""
    def __init__(self, message: str = "Invalid API token", **kwargs):
        super().__init__(status_code=401, message=message, **kwargs)

    def __str__(self):
        return f"APIKeyInvalidError: {self.message}"

