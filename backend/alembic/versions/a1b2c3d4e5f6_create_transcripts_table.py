"""create_transcripts_table

Revision ID: a1b2c3d4e5f6
Revises: f7d0adaac219
Create Date: 2025-11-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f7d0adaac219'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('transcripts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('speaker_type', sa.String(length=20), nullable=False),
        sa.Column('speaker_id', sa.UUID(), nullable=True),
        sa.Column('speaker_name', sa.String(length=255), nullable=False),
        sa.Column('transcript_text', sa.Text(), nullable=False),
        sa.Column('timestamp_start', sa.DateTime(), nullable=False),
        sa.Column('timestamp_end', sa.DateTime(), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('location_name', sa.String(length=500), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcripts_user_id'), 'transcripts', ['user_id'], unique=False)
    op.create_index(op.f('ix_transcripts_session_id'), 'transcripts', ['session_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_transcripts_session_id'), table_name='transcripts')
    op.drop_index(op.f('ix_transcripts_user_id'), table_name='transcripts')
    op.drop_table('transcripts')
