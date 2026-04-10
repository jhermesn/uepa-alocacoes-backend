from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
import datetime

class CacheEntry(Base):
    __tablename__ = "cache_entries"

    key = Column(String, primary_key=True, index=True)
    value = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    def is_expired(self) -> bool:
        return datetime.datetime.now(datetime.timezone.utc) > self.expires_at
