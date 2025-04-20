from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class LogEntryBase(BaseModel):
    timestamp: datetime
    level: str
    message: str
    source: Optional[str] = None

class LogEntryCreate(LogEntryBase):
    pass

class LogEntryRead(LogEntryBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True
