from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.cache import CacheEntry
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

class CacheRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> Optional[Any]:
        now = datetime.now(timezone.utc)
        entry = self.db.query(CacheEntry).filter(
            CacheEntry.key == key,
            CacheEntry.expires_at > now
        ).first()
        
        return entry.value if entry else None

    def set(self, key: str, value: Any, ttl_seconds: int = 600):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        

        stmt = insert(CacheEntry).values(
            key=key,
            value=value,
            expires_at=expires_at
        )
        

        stmt = stmt.on_conflict_do_update(
            index_elements=['key'],
            set_={
                'value': stmt.excluded.value,
                'expires_at': stmt.excluded.expires_at
            }
        )
        
        self.db.execute(stmt)
        self.db.commit()

    def invalidate_pattern(self, pattern: str):
        """Deletes all keys starting with the specified pattern."""
        self.db.query(CacheEntry).filter(CacheEntry.key.like(f"{pattern}%")).delete(synchronize_session=False)
        self.db.commit()

    def clear_expired(self):
        now = datetime.now(timezone.utc)
        self.db.query(CacheEntry).filter(CacheEntry.expires_at <= now).delete()
        self.db.commit()
