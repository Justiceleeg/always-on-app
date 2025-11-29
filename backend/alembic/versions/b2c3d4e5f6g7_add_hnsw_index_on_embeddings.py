"""add_hnsw_index_on_embeddings

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add HNSW index on embeddings for fast vector similarity search."""
    # Create HNSW index for vector similarity search
    # Parameters:
    # - m = 16: Number of bi-directional links for each node (default is 16)
    # - ef_construction = 64: Size of dynamic list for constructing the graph (higher = better quality, slower build)
    # Using vector_cosine_ops for cosine similarity
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transcripts_embedding
        ON transcripts USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)


def downgrade() -> None:
    """Remove HNSW index."""
    op.execute("DROP INDEX IF EXISTS idx_transcripts_embedding;")
