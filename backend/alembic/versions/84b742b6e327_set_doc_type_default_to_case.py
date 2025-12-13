"""set_doc_type_default_to_case

Revision ID: 84b742b6e327
Revises: 4fb8f520f189
Create Date: 2025-12-12 21:45:38.094247

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '84b742b6e327'
down_revision = '4fb8f520f189'
branch_labels = None
depends_on = None


def upgrade():
    # Обновляем существующие NULL значения на 'CASE'
    op.execute("UPDATE documents SET doc_type = 'CASE' WHERE doc_type IS NULL")
    
    # Устанавливаем server_default для doc_type
    op.alter_column('documents', 'doc_type',
                    existing_type=sa.String(length=50),
                    nullable=False,
                    server_default='CASE')


def downgrade():
    # Убираем server_default
    op.alter_column('documents', 'doc_type',
                    existing_type=sa.String(length=50),
                    nullable=True,
                    server_default=None)

