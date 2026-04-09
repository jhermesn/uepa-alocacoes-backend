"""create_cache_table

Revision ID: 7e3b54c436f1
Revises: 8e9a7ae084c1
Create Date: 2026-04-09 01:15:01.834184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e3b54c436f1'
down_revision: Union[str, Sequence[str], None] = '8e9a7ae084c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE UNLOGGED TABLE cache_entries (
            key TEXT PRIMARY KEY,
            value JSONB NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL
        );
    """)
    op.create_index('ix_cache_entries_expires_at', 'cache_entries', ['expires_at'])
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_cache_entries_expires_at')
    op.drop_table('cache_entries')
    pass
