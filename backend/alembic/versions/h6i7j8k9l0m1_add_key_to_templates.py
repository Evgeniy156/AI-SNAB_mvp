"""add key to templates

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2025-12-13 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h6i7j8k9l0m1'
down_revision = 'g5h6i7j8k9l0'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем колонку key в templates
    op.add_column('templates', sa.Column('key', sa.String(length=100), nullable=True))
    # Создаём unique constraint на key
    op.create_unique_constraint('uq_templates_key', 'templates', ['key'])


def downgrade():
    # Удаляем unique constraint и колонку
    op.drop_constraint('uq_templates_key', 'templates', type_='unique')
    op.drop_column('templates', 'key')

