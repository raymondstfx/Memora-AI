"""add entities aliases temporal memory and provenance relations

Revision ID: 0005_memories
Revises: 0004_meetings
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_memories"
down_revision = "0004_meetings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("canonical_name", sa.String(length=180), nullable=False),
        sa.Column("normalized_name", sa.String(length=180), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("merged_into_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_id"],
            ["entities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", "normalized_name"),
    )
    op.create_index(op.f("ix_entities_user_id"), "entities", ["user_id"], unique=False)
    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("normalized_name", sa.String(length=180), nullable=False),
        sa.Column("confirmed_by_user", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", "normalized_name"),
    )
    op.create_index(
        op.f("ix_entity_aliases_entity_id"),
        "entity_aliases",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_aliases_user_id"), "entity_aliases", ["user_id"], unique=False
    )
    op.create_table(
        "memories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("subject_entity_id", sa.Uuid(), nullable=False),
        sa.Column("predicate", sa.String(length=50), nullable=False),
        sa.Column("slot_key", sa.String(length=120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("memory_type", sa.String(length=30), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_quote", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Double(), nullable=False),
        sa.Column("evidence_kind", sa.String(length=30), nullable=False),
        sa.Column("lifecycle", sa.String(length=30), nullable=False),
        sa.Column("review_state", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', search_text)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["meetings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subject_entity_id"],
            ["entities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["memories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_key"),
    )
    op.create_index(
        op.f("ix_memories_meeting_id"), "memories", ["meeting_id"], unique=False
    )
    op.create_index(
        op.f("ix_memories_message_id"), "memories", ["message_id"], unique=False
    )
    op.create_index(
        op.f("ix_memories_source_id"), "memories", ["source_id"], unique=False
    )
    op.create_index(op.f("ix_memories_status"), "memories", ["status"], unique=False)
    op.create_index(
        op.f("ix_memories_subject_entity_id"),
        "memories",
        ["subject_entity_id"],
        unique=False,
    )
    op.create_index(op.f("ix_memories_user_id"), "memories", ["user_id"], unique=False)
    op.create_index(
        "ix_memory_search",
        "memories",
        ["search_tsv"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_memory_slot_time",
        "memories",
        ["user_id", "subject_entity_id", "slot_key", "valid_from"],
        unique=False,
    )
    op.create_table(
        "entity_relations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("from_entity_id", sa.Uuid(), nullable=False),
        sa.Column("to_entity_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(length=50), nullable=False),
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_entity_id"],
            ["entities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["memory_id"],
            ["memories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["to_entity_id"],
            ["entities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("memory_id", "relation"),
    )
    op.create_index(
        op.f("ix_entity_relations_from_entity_id"),
        "entity_relations",
        ["from_entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_relations_memory_id"),
        "entity_relations",
        ["memory_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_relations_to_entity_id"),
        "entity_relations",
        ["to_entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_relations_user_id"),
        "entity_relations",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_entity_relations_user_id"), table_name="entity_relations")
    op.drop_index(
        op.f("ix_entity_relations_to_entity_id"), table_name="entity_relations"
    )
    op.drop_index(op.f("ix_entity_relations_memory_id"), table_name="entity_relations")
    op.drop_index(
        op.f("ix_entity_relations_from_entity_id"), table_name="entity_relations"
    )
    op.drop_table("entity_relations")
    op.drop_index("ix_memory_slot_time", table_name="memories")
    op.drop_index("ix_memory_search", table_name="memories", postgresql_using="gin")
    op.drop_index(op.f("ix_memories_user_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_subject_entity_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_status"), table_name="memories")
    op.drop_index(op.f("ix_memories_source_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_message_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_meeting_id"), table_name="memories")
    op.drop_table("memories")
    op.drop_index(op.f("ix_entity_aliases_user_id"), table_name="entity_aliases")
    op.drop_index(op.f("ix_entity_aliases_entity_id"), table_name="entity_aliases")
    op.drop_table("entity_aliases")
    op.drop_index(op.f("ix_entities_user_id"), table_name="entities")
    op.drop_table("entities")
