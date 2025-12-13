"""supplier profile tables

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2025-12-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    # Создание таблицы supplier_profiles
    op.create_table(
        'supplier_profiles',
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('full_name', sa.Text(), nullable=True),
        sa.Column('short_name', sa.Text(), nullable=True),
        sa.Column('ogrn', sa.String(length=20), nullable=True),
        sa.Column('okpo', sa.String(length=20), nullable=True),
        sa.Column('okato', sa.String(length=20), nullable=True),
        sa.Column('kpp', sa.String(length=9), nullable=True),
        sa.Column('inn', sa.String(length=12), nullable=True),
        sa.Column('legal_address', sa.Text(), nullable=True),
        sa.Column('fact_address', sa.Text(), nullable=True),
        sa.Column('mail_address', sa.Text(), nullable=True),
        sa.Column('postal_code', sa.String(length=10), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('contact_position', sa.String(length=255), nullable=True),
        sa.Column('business_description', sa.Text(), nullable=True),
        sa.Column('main_products_services', sa.Text(), nullable=True),
        sa.Column('industries', sa.Text(), nullable=True),
        sa.Column('production_sites', sa.Text(), nullable=True),
        sa.Column('capacity_description', sa.Text(), nullable=True),
        sa.Column('equipment_summary', sa.Text(), nullable=True),
        sa.Column('headcount_total', sa.Integer(), nullable=True),
        sa.Column('headcount_engineering', sa.Integer(), nullable=True),
        sa.Column('headcount_production', sa.Integer(), nullable=True),
        sa.Column('headcount_quality', sa.Integer(), nullable=True),
        sa.Column('key_specialists', sa.Text(), nullable=True),
        sa.Column('has_qms', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('qms_standards', sa.String(length=255), nullable=True),
        sa.Column('certifications_summary', sa.Text(), nullable=True),
        sa.Column('works_with_goz', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('goz_experience', sa.Text(), nullable=True),
        sa.Column('goz_secret_clearance', sa.Boolean(), nullable=True),
        sa.Column('executed_contracts_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('key_customers', sa.Text(), nullable=True),
        sa.Column('similar_deliveries', sa.Text(), nullable=True),
        sa.Column('bank_name', sa.String(length=255), nullable=True),
        sa.Column('bank_bik', sa.String(length=20), nullable=True),
        sa.Column('bank_account', sa.String(length=50), nullable=True),
        sa.Column('corr_account', sa.String(length=50), nullable=True),
        sa.Column('signatory_fio', sa.String(length=255), nullable=True),
        sa.Column('signatory_position', sa.String(length=255), nullable=True),
        sa.Column('signatory_basis', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
    )
    
    # Создание таблицы okved_codes
    op.create_table(
        'okved_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=20), nullable=False, unique=True),
        sa.Column('name', sa.String(length=500), nullable=True),
    )
    
    # Создание таблицы supplier_okved
    op.create_table(
        'supplier_okved',
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('okved_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['okved_id'], ['okved_codes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('supplier_id', 'okved_id'),
        sa.UniqueConstraint('supplier_id', 'okved_id', name='uq_supplier_okved'),
    )
    
    # Создание таблицы supplier_equipment
    op.create_table(
        'supplier_equipment',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('qty', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
    )
    
    # Создание таблицы supplier_certificates
    op.create_table(
        'supplier_certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cert_type', sa.String(length=100), nullable=False),
        sa.Column('number', sa.String(length=100), nullable=True),
        sa.Column('issued_by', sa.String(length=255), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
    )
    
    # Добавление supplier_id в documents (nullable)
    op.add_column('documents', sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_documents_supplier_id',
        'documents', 'suppliers',
        ['supplier_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Делаем case_id nullable (так как документ может быть либо у case, либо у supplier)
    op.alter_column('documents', 'case_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)


def downgrade():
    # Возвращаем case_id NOT NULL
    op.alter_column('documents', 'case_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    
    # Удаляем supplier_id из documents
    op.drop_constraint('fk_documents_supplier_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'supplier_id')
    
    # Удаляем таблицы
    op.drop_table('supplier_certificates')
    op.drop_table('supplier_equipment')
    op.drop_table('supplier_okved')
    op.drop_table('okved_codes')
    op.drop_table('supplier_profiles')

