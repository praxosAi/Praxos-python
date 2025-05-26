# my_api_sdk/__init__.py
"""
My Awesome API SDK - Final Refactor with Model Separation!
"""
from .config import ClientConfig, DEFAULT_BASE_URL, SDK_VERSION
from .exceptions import APIError

# Client Imports
from .client import SyncClient

# Model/Resource Imports (these are the classes users will interact with)
from .models import (
    SyncEnvironment,
    SyncSource,
)


__all__ = [
    # Config and Exceptions
    'ClientConfig',
    'DEFAULT_BASE_URL',
    'SDK_VERSION',
    'APIError',

    # Sync components
    'SyncClient',
    'SyncEnvironment',
    'SyncSource',
]

__version__ = SDK_VERSION