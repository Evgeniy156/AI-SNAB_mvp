"""procurement checklist tables

Revision ID: c1d2e3f4a5b6
Revises: 84b742b6e327
Create Date: 2025-12-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = '84b742b6e327'
branch_labels = None
depends_on = None


def upgrade():
    # Создание таблицы checklist_templates
    op.create_table(
        'checklist_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(length=100), nullable=False, unique=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Создание таблицы checklist_template_items
    op.create_table(
        'checklist_template_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section', sa.String(length=200), nullable=False),
        sa.Column('group_title', sa.String(length=200), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('hint', sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['checklist_templates.id'], ondelete='CASCADE'),
    )
    
    # Индекс для сортировки
    op.create_index(
        'ix_checklist_template_items_template_sort',
        'checklist_template_items',
        ['template_id', 'sort_order']
    )
    
    # Создание таблицы case_checklist_items
    op.create_table(
        'case_checklist_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='TODO'),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_item_id'], ['checklist_template_items.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('case_id', 'template_item_id', name='uq_case_checklist_item'),
    )
    
    # Создание таблицы case_checklist_item_documents
    op.create_table(
        'case_checklist_item_documents',
        sa.Column('case_checklist_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['case_checklist_item_id'], ['case_checklist_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('case_checklist_item_id', 'document_id'),
        sa.UniqueConstraint('case_checklist_item_id', 'document_id', name='uq_checklist_item_document'),
    )
    
    # Добавление поля epoz_clause в cases
    op.add_column('cases', sa.Column('epoz_clause', sa.String(length=50), nullable=True))


def downgrade():
    # Удаление поля epoz_clause из cases
    op.drop_column('cases', 'epoz_clause')
    
    # Удаление таблиц
    op.drop_table('case_checklist_item_documents')
    op.drop_table('case_checklist_items')
    op.drop_index('ix_checklist_template_items_template_sort', table_name='checklist_template_items')
    op.drop_table('checklist_template_items')
    op.drop_table('checklist_templates')

