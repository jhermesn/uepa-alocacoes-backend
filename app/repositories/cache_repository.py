import hashlib
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timedelta, timezone
from app.models.cache import CacheEntry

class CacheRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def generate_key(prefix: str, **kwargs) -> str:
        """Deterministic key generation: prefix_hash"""
        query_parts = [f"{k}:{v}" for k, v in sorted(kwargs.items())]
        query_str = "_".join(query_parts)
        hash_sig = hashlib.md5(query_str.encode()).hexdigest()
        return f"{prefix}_{hash_sig}"

    def get(self, key: str) -> Optional[Any]:
        now = datetime.now(timezone.utc)
        entry = self.db.query(CacheEntry).filter(
            CacheEntry.key == key,
            CacheEntry.expires_at > now
        ).first()
        return entry.value if entry else None

    def set(self, key: str, value: Any, ttl: int):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        
        stmt = insert(CacheEntry).values(
            key=key,
            value=value,
            expires_at=expires_at
        ).on_conflict_do_update(
            index_elements=['key'],
            set_={
                'value': value,
                'expires_at': expires_at
            }
        )
        self.db.execute(stmt)
        self.db.commit()

    def invalidate_pattern(self, prefix: str):
        self.db.query(CacheEntry).filter(
            CacheEntry.key.like(f"{prefix}%")
        ).delete(synchronize_session=False)
        self.db.commit()
