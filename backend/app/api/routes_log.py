import re
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.log_entry import LogEntry
from app.models import LogUpload
from app.db.session import get_db
from datetime import datetime

LOG_REGEX = re.compile(r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>INFO|WARNING|ERROR|DEBUG) (?P<message>.*)")

router = APIRouter()

from app.utils.log_parsers import ALL_PARSERS

@router.post("/upload-log")
def upload_log(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Accepts a .log file, auto-detects among 10 common formats, parses each line, and stores valid entries in the database.
    Returns the number of lines parsed, lines failed, upload_id, and per-format stats.
    """
    import json
    try:
        if not file.filename.endswith('.log'):
            raise HTTPException(status_code=400, detail="Only .log files are accepted")
        content = file.file.read().decode('utf-8')
        lines = content.splitlines()
        entries = []
        failed_lines = []
        format_counts = {}
        format_failed = {}
        tz = pytz.timezone('Asia/Kolkata')
        # For multiline parsers, buffer lines
        i = 0
        while i < len(lines):
            line = lines[i]
            matched = False
            for parser in ALL_PARSERS:
                if parser.multiline:
                    # Try up to 10 lines as a block
                    for j in range(2, min(10, len(lines)-i)+1):
                        block = lines[i:i+j]
                        result = parser.match(block)
                        if result:
                            norm = parser.normalize(result, file.filename)
                            entries.append(LogEntry(
                                timestamp=norm['timestamp'],
                                level=norm['level'],
                                message=norm['message'],
                                source=norm['source'],
                            ))
                            format_counts[parser.name] = format_counts.get(parser.name, 0) + 1
                            i += j-1
                            matched = True
                            break
                    if matched:
                        break
                else:
                    result = parser.match(line)
                    if result:
                        norm = parser.normalize(result, file.filename)
                        entries.append(LogEntry(
                            timestamp=norm['timestamp'],
                            level=norm['level'],
                            message=norm['message'],
                            source=norm['source'],
                        ))
                        format_counts[parser.name] = format_counts.get(parser.name, 0) + 1
                        matched = True
                        break
            if not matched:
                failed_lines.append(line)
                # Optionally count which parser failed most on this line
            i += 1
        log_upload = LogUpload(
            filename=file.filename,
            uploaded_at=datetime.utcnow(),
            lines_parsed=len(entries),
            lines_failed=len(failed_lines)
        )
        db.add(log_upload)
        db.flush()  # Get log_upload.id
        for entry in entries:
            entry.log_upload_id = log_upload.id
            db.add(entry)
        try:
            db.commit()
        except Exception as db_exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"DB error: {str(db_exc)}")
        return {
            "status": "success",
            "lines_parsed": len(entries),
            "lines_read": len(lines),
            "lines_failed_to_parse": len(failed_lines),
            "formats_detected": format_counts,
            "upload_id": str(log_upload.id),
            "lines_failed_examples": failed_lines[:5]
        }
    except HTTPException as he:
        raise he
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}")


@router.get("/uploads")
def list_uploads(db: Session = Depends(get_db)):
    uploads = db.query(LogUpload).order_by(LogUpload.uploaded_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "filename": u.filename,
            "uploaded_at": u.uploaded_at.isoformat(),
            "lines_parsed": u.lines_parsed,
            "lines_failed": u.lines_failed
        }
        for u in uploads
    ]


@router.get("/uploads/{upload_id}/logs")
def logs_by_upload(upload_id: str, db: Session = Depends(get_db)):
    logs = db.query(LogEntry).filter(LogEntry.log_upload_id == upload_id).order_by(LogEntry.timestamp.asc()).all()
    return [
        {
            "id": str(l.id),
            "timestamp": l.timestamp.isoformat(),
            "level": l.level,
            "message": l.message,
            "source": l.source,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]


from typing import List, Optional
from fastapi import Query, Response
from app.schemas.log_entry import LogEntryRead
from sqlalchemy import desc, asc, func
import csv
import io
import pytz

@router.get("/logs/summary")
def logs_summary(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    from collections import OrderedDict
    # Use Asia/Kolkata local timezone for all summaries
    tz = pytz.timezone('Asia/Kolkata')
    levels = ['ERROR', 'WARNING', 'INFO', 'DEBUG']
    counts_by_level = dict(
        db.query(LogEntry.level, func.count(LogEntry.id))
        .filter(LogEntry.level.in_(levels))
        .group_by(LogEntry.level)
        .all()
    )
    for lvl in levels:
        counts_by_level.setdefault(lvl, 0)

    # Log counts by hour for last 24 hours, using local time
    now = datetime.now(tz)
    # Round down to the current hour
    now = now.replace(minute=0, second=0, microsecond=0)
    last_24h = now - timedelta(hours=23)
    # Get all logs in last 24h (in UTC, but convert to local time for bucketing)
    logs = db.query(LogEntry.timestamp).filter(LogEntry.timestamp >= last_24h.astimezone(pytz.UTC)).all()
    # Bucket logs by local hour
    hourly = {}
    for (ts,) in logs:
        # Ensure ts is timezone-aware in UTC, then convert to local
        if ts.tzinfo is None:
            ts = pytz.UTC.localize(ts)
        local_ts = ts.astimezone(tz)
        hour_bucket = local_ts.replace(minute=0, second=0, microsecond=0)
        hour_str = hour_bucket.strftime('%Y-%m-%d %H:00')
        hourly[hour_str] = hourly.get(hour_str, 0) + 1
    # Fill missing hours
    hours = [ (now - timedelta(hours=i)) for i in reversed(range(24)) ]
    hourly_filled = OrderedDict()
    for h in hours:
        key = h.strftime('%Y-%m-%d %H:00')
        hourly_filled[key] = hourly.get(key, 0)
    return { 'counts_by_level': counts_by_level, 'counts_by_hour': hourly_filled }

from datetime import datetime
from sqlalchemy import or_, and_

from fastapi.responses import StreamingResponse, JSONResponse
from collections import Counter
import re

@router.get("/logs/export")
def export_logs(
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    logic: str = Query("AND", regex="^(AND|OR)$"),
    format: str = Query("csv", regex="^(csv|json)$"),
    db: Session = Depends(get_db)
):
    filters = []
    if level:
        filters.append(LogEntry.level == level)
    if search:
        filters.append(LogEntry.message.ilike(f"%{search}%"))
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            filters.append(LogEntry.timestamp >= from_dt)
        except Exception:
            pass
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            filters.append(LogEntry.timestamp <= to_dt)
        except Exception:
            pass
    if filters:
        if logic == "AND":
            query = db.query(LogEntry).filter(and_(*filters))
        else:
            query = db.query(LogEntry).filter(or_(*filters))
    else:
        query = db.query(LogEntry)
    logs = query.order_by(desc(LogEntry.timestamp)).all()
    # CSV export
    if format == "csv":
        def iter_csv():
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "timestamp", "level", "message", "source", "created_at"])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            for log in logs:
                writer.writerow([
                    log.id,
                    log.timestamp.isoformat() if log.timestamp else "",
                    log.level,
                    log.message,
                    log.source or "",
                    log.created_at.isoformat() if log.created_at else "",
                ])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
        return StreamingResponse(iter_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=logs.csv"})
    # JSON export
    else:
        data = [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "level": log.level,
                "message": log.message,
                "source": log.source,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
        return JSONResponse(content=data, headers={"Content-Disposition": "attachment; filename=logs.json"})

@router.get("/logs/report")
def logs_report(
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    logic: str = Query("AND", regex="^(AND|OR)$"),
    db: Session = Depends(get_db)
):
    filters = []
    if level:
        filters.append(LogEntry.level == level)
    if search:
        filters.append(LogEntry.message.ilike(f"%{search}%"))
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            filters.append(LogEntry.timestamp >= from_dt)
        except Exception:
            pass
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            filters.append(LogEntry.timestamp <= to_dt)
        except Exception:
            pass
    if filters:
        if logic == "AND":
            query = db.query(LogEntry).filter(and_(*filters))
        else:
            query = db.query(LogEntry).filter(or_(*filters))
    else:
        query = db.query(LogEntry)
    logs = query.order_by(desc(LogEntry.timestamp)).all()
    # Most frequent log levels
    level_counts = Counter(log.level for log in logs)
    most_frequent_levels = level_counts.most_common()
    # Common keywords
    keywords = ["timeout", "failed", "crash", "error", "disconnect", "denied", "exception", "restart", "unavailable", "slow", "unreachable"]
    keyword_counts = Counter()
    for log in logs:
        msg = (log.message or "").lower()
        for kw in keywords:
            if re.search(rf"\\b{re.escape(kw)}\\b", msg):
                keyword_counts[kw] += 1
    common_keywords = keyword_counts.most_common()
    # Suggested actions
    suggestions = []
    if level_counts.get("ERROR", 0) > 10:
        suggestions.append("High error volume detected. Investigate recent errors.")
    if keyword_counts.get("timeout", 0) > 0:
        suggestions.append("Investigate DB/network timeouts.")
    if keyword_counts.get("crash", 0) > 0:
        suggestions.append("Check for application crashes.")
    if keyword_counts.get("failed", 0) > 0:
        suggestions.append("Review failed operations.")
    if not suggestions:
        suggestions.append("No critical issues detected.")
    return {
        "most_frequent_levels": most_frequent_levels,
        "common_keywords": common_keywords,
        "suggested_actions": suggestions
    }

@router.get("/logs", response_model=List[LogEntryRead])
def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    search: Optional[str] = Query(None, description="Keyword to search in log message"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    logic: str = Query("AND", regex="^(AND|OR)$", description="Combine filters with AND/OR"),
    limit: int = Query(100, gt=0, le=1000, description="Number of logs to return (default 100, max 1000)"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order: asc or desc"),
    db: Session = Depends(get_db)
):
    filters = []
    if level:
        filters.append(LogEntry.level == level)
    if search:
        filters.append(LogEntry.message.ilike(f"%{search}%"))
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            filters.append(LogEntry.timestamp >= from_dt)
        except Exception:
            pass
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            filters.append(LogEntry.timestamp <= to_dt)
        except Exception:
            pass
    if filters:
        if logic == "AND":
            query = db.query(LogEntry).filter(and_(*filters))
        else:
            query = db.query(LogEntry).filter(or_(*filters))
    else:
        query = db.query(LogEntry)
    sort_order = desc(LogEntry.timestamp) if order == "desc" else asc(LogEntry.timestamp)
    logs = query.order_by(sort_order).limit(limit).all()
    return logs

