"""activation gate + basis doc fields

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2025-12-13 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем поля активации в cases
    op.add_column('cases', sa.Column('is_activated', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('cases', sa.Column('activated_at', sa.DateTime(), nullable=True))
    
    # Добавляем поля номера и даты документа в case_checklist_items
    op.add_column('case_checklist_items', sa.Column('doc_number', sa.String(length=100), nullable=True))
    op.add_column('case_checklist_items', sa.Column('doc_date', sa.Date(), nullable=True))


def downgrade():
    # Удаляем поля
    op.drop_column('case_checklist_items', 'doc_date')
    op.drop_column('case_checklist_items', 'doc_number')
    op.drop_column('cases', 'activated_at')
    op.drop_column('cases', 'is_activated')

