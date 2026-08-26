from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.storage.local import LocalStorageProvider


@lru_cache
def get_storage_provider() -> LocalStorageProvider:
    """create one reusable local storage provider per app process"""
    return LocalStorageProvider(Path(settings.LOCAL_STORAGE_PATH))
