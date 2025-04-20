import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class LogUpload(Base):
    __tablename__ = "log_uploads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    lines_parsed = Column(Integer, nullable=False)
    lines_failed = Column(Integer, nullable=False)
    log_entries = relationship("LogEntry", back_populates="upload")

class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    log_upload_id = Column(UUID(as_uuid=True), ForeignKey('log_uploads.id'), nullable=True)
    upload = relationship("LogUpload", back_populates="log_entries")
