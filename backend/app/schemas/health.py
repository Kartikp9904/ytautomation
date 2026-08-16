from pydantic import BaseModel
from typing import Dict, Any, Optional


class StorageHealth(BaseModel):
    provider: str
    connected: bool
    free_space_gb: Optional[float] = None
    total_space_gb: Optional[float] = None


class SystemHealthResponse(BaseModel):
    status: str
    environment: str
    database: str
    scheduler: str
    storage: StorageHealth
    timestamp: str
    version: str = "1.0.0"
