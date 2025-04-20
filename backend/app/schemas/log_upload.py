from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class LogUploadBase(BaseModel):
    filename: str
    uploaded_at: datetime
    lines_parsed: int
    lines_failed: int

class LogUploadCreate(LogUploadBase):
    pass

class LogUploadRead(LogUploadBase):
    id: UUID

    class Config:
        orm_mode = True
