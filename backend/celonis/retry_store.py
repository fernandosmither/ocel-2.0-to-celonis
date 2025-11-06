import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _default_storage_dir() -> Path:
    """Return the default directory where failed requests are stored."""
    base_dir = Path(__file__).resolve().parent.parent / "storage" / "failed_requests"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def _json_serialize(value: Any) -> Any:
    """Best-effort conversion of values to JSON-serialisable structures."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_serialize(v) for v in list(value)]
    return repr(value)


@dataclass
class FailureAttempt:
    """Represents a single failed attempt to execute a request."""

    timestamp: str
    status_code: int
    message: str
    response_body: Optional[str] = None


@dataclass
class FailedRequestRecord:
    """Represents the payload persisted for failed Celonis requests."""

    id: str
    created_at: str
    operation: str
    metadata: Dict[str, Any]
    request: Dict[str, Any]
    attempts: List[FailureAttempt] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "operation": self.operation,
            "metadata": _json_serialize(self.metadata),
            "request": _json_serialize(self.request),
            "attempts": [
                {
                    "timestamp": attempt.timestamp,
                    "status_code": attempt.status_code,
                    "message": attempt.message,
                    "response_body": attempt.response_body,
                }
                for attempt in self.attempts
            ],
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "FailedRequestRecord":
        return cls(
            id=data["id"],
            created_at=data["created_at"],
            operation=data.get("operation", "unknown_operation"),
            metadata=data.get("metadata", {}),
            request=data.get("request", {}),
            attempts=[
                FailureAttempt(
                    timestamp=attempt.get("timestamp", ""),
                    status_code=attempt.get("status_code", 0),
                    message=attempt.get("message", ""),
                    response_body=attempt.get("response_body"),
                )
                for attempt in data.get("attempts", [])
            ],
        )

    def summary(self) -> Dict[str, Any]:
        last_attempt = self.attempts[-1] if self.attempts else None
        return {
            "id": self.id,
            "operation": self.operation,
            "created_at": self.created_at,
            "metadata": _json_serialize(self.metadata),
            "attempt_count": len(self.attempts),
            "last_status_code": getattr(last_attempt, "status_code", None),
            "last_message": getattr(last_attempt, "message", None),
        }


class FailedRequestStore:
    """Persistent storage for failed Celonis requests."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or _default_storage_dir()
        self._lock = asyncio.Lock()

    def _record_path(self, record_id: str) -> Path:
        return self.storage_dir / f"{record_id}.json"

    async def _read_record(self, path: Path) -> FailedRequestRecord:
        data = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return FailedRequestRecord.from_json(json.loads(data))

    async def _write_record(self, record: FailedRequestRecord) -> None:
        path = self._record_path(record.id)
        payload = json.dumps(record.to_json(), indent=2, ensure_ascii=True)
        await asyncio.to_thread(path.write_text, payload, encoding="utf-8")

    async def all_records(self) -> List[FailedRequestRecord]:
        """Return every persisted record."""
        records: List[FailedRequestRecord] = []
        for path in sorted(self.storage_dir.glob("*.json")):
            try:
                record = await self._read_record(path)
                records.append(record)
            except Exception:
                # Skip corrupted files but keep going
                continue
        return records

    async def record_failure(
        self,
        *,
        operation: str,
        metadata: Optional[Dict[str, Any]],
        request: Dict[str, Any],
        status_code: int,
        message: str,
        response_body: Optional[str],
    ) -> FailedRequestRecord:
        """Persist a newly failed request."""
        record = FailedRequestRecord(
            id=str(uuid.uuid4()),
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            operation=operation,
            metadata=metadata or {},
            request=_json_serialize(request),
            attempts=[
                FailureAttempt(
                    timestamp=datetime.now(tz=timezone.utc).isoformat(),
                    status_code=status_code,
                    message=message,
                    response_body=response_body,
                )
            ],
        )
        async with self._lock:
            await self._write_record(record)
        return record

    async def append_attempt(
        self,
        record_id: str,
        *,
        status_code: int,
        message: str,
        response_body: Optional[str],
    ) -> Optional[FailedRequestRecord]:
        """Append an additional attempt to an existing record."""
        path = self._record_path(record_id)
        if not path.exists():
            return None

        async with self._lock:
            record = await self._read_record(path)
            record.attempts.append(
                FailureAttempt(
                    timestamp=datetime.now(tz=timezone.utc).isoformat(),
                    status_code=status_code,
                    message=message,
                    response_body=response_body,
                )
            )
            await self._write_record(record)
            return record

    async def delete(self, record_id: str) -> bool:
        """Delete a persisted record once it has been successfully retried."""
        path = self._record_path(record_id)
        if not path.exists():
            return False
        async with self._lock:
            await asyncio.to_thread(path.unlink)
        return True

    async def clear(self) -> None:
        """Remove every persisted failed request."""
        async with self._lock:
            for path in self.storage_dir.glob("*.json"):
                await asyncio.to_thread(path.unlink)

    async def summary(self) -> Dict[str, Any]:
        """Return a summary view of all failed requests."""
        records = await self.all_records()
        records.sort(key=lambda r: r.created_at)
        return {
            "total": len(records),
            "records": [record.summary() for record in records],
        }


_singleton_store: Optional[FailedRequestStore] = None


def get_failed_request_store() -> FailedRequestStore:
    """Return a shared instance of the store."""
    global _singleton_store
    if _singleton_store is None:
        _singleton_store = FailedRequestStore()
    return _singleton_store
