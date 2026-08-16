from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class DriveAuthUrlResponse(BaseModel):
    auth_url: str


class DriveCallbackRequest(BaseModel):
    code: str


class DriveStatusResponse(BaseModel):
    connected: bool
    account_email: Optional[str] = None
    has_credentials: bool
    token_expiry: Optional[str] = None
    last_error: Optional[str] = None
    storage_provider: str


class DriveFolderItemResponse(BaseModel):
    id: str
    name: str
    path: str
    parent_id: Optional[str] = None
    modified_time: Optional[str] = None


class ScanTriggerRequest(BaseModel):
    root_folder_id: Optional[str] = Field(default=None, description="Drive folder ID or local folder path")
    channel_id: Optional[str] = Field(default=None, description="Optional channel ID to associate scanned folders with")
    provider: Optional[str] = Field(default=None, description="'google_drive' or 'local'")


class ScanSummaryResponse(BaseModel):
    root_id: str
    folders_found: int
    videos_found: int
    sidecar_json_found: int
    thumbnails_found: int
    errors: List[str] = []
