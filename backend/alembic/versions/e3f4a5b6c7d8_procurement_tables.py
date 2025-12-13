"""procurement tables

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2025-12-13 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade():
    # Расширение таблицы cases
    op.add_column('cases', sa.Column('procurement_type', sa.String(length=50), nullable=False, server_default='GOODS_SUPPLY'))
    op.add_column('cases', sa.Column('subject', sa.Text(), nullable=True))
    op.add_column('cases', sa.Column('initiator_department', sa.String(length=255), nullable=True))
    op.add_column('cases', sa.Column('planned_deadline', sa.Date(), nullable=True))
    op.add_column('cases', sa.Column('procedure_stage', sa.String(length=50), nullable=False, server_default='DRAFT'))
    op.add_column('cases', sa.Column('nmc_avg_price', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('cases', sa.Column('validation_coeff', sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column('cases', sa.Column('offers_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('cases', sa.Column('is_validation_ok', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('cases', sa.Column('selected_supplier_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('cases', sa.Column('selection_note', sa.Text(), nullable=True))
    
    # FK для selected_supplier_id
    op.create_foreign_key(
        'fk_cases_selected_supplier_id',
        'cases', 'suppliers',
        ['selected_supplier_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создание таблицы case_candidates
    op.create_table(
        'case_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('org_name', sa.String(length=255), nullable=False),
        sa.Column('inn', sa.String(length=20), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NEW'),
        sa.Column('rank_score', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('rank_explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
    )
    
    # Создание таблицы rfq_requests
    op.create_table(
        'rfq_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('result', sa.String(length=50), nullable=False, server_default='SENT'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('evidence_document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['case_candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_document_id'], ['documents.id'], ondelete='SET NULL'),
    )
    
    # Создание таблицы commercial_offers
    op.create_table(
        'commercial_offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('price_total', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='RUB'),
        sa.Column('vat_included', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('delivery_terms', sa.Text(), nullable=True),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['case_candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    )
    
    # Создание таблицы supplier_security_reviews
    op.create_table(
        'supplier_security_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NOT_STARTED'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('case_id', 'supplier_id', name='uq_case_supplier_security_review'),
    )


def downgrade():
    # Удаление таблиц
    op.drop_table('supplier_security_reviews')
    op.drop_table('commercial_offers')
    op.drop_table('rfq_requests')
    op.drop_table('case_candidates')
    
    # Удаление FK и колонок из cases
    op.drop_constraint('fk_cases_selected_supplier_id', 'cases', type_='foreignkey')
    op.drop_column('cases', 'selection_note')
    op.drop_column('cases', 'selected_supplier_id')
    op.drop_column('cases', 'is_validation_ok')
    op.drop_column('cases', 'offers_count')
    op.drop_column('cases', 'validation_coeff')
    op.drop_column('cases', 'nmc_avg_price')
    op.drop_column('cases', 'procedure_stage')
    op.drop_column('cases', 'planned_deadline')
    op.drop_column('cases', 'initiator_department')
    op.drop_column('cases', 'subject')
    op.drop_column('cases', 'procurement_type')

