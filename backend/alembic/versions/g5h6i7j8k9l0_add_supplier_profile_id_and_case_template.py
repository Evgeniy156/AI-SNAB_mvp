"""add supplier_profile id and case checklist_template_id

Revision ID: g5h6i7j8k9l0
Revises: f4a5b6c7d8e9
Create Date: 2025-12-13 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'g5h6i7j8k9l0'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем id в supplier_profiles
    # Сначала создаём новую колонку id как nullable
    op.add_column('supplier_profiles', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Заполняем id для существующих записей
    # Используем gen_random_uuid() (PostgreSQL 13+), если не доступно - uuid_generate_v4()
    # Проверяем версию PostgreSQL и используем соответствующую функцию
    from sqlalchemy import text
    connection = op.get_bind()
    
    # Пробуем использовать gen_random_uuid() (PostgreSQL 13+)
    try:
        connection.execute(text("SELECT gen_random_uuid()"))
        uuid_func = "gen_random_uuid()"
    except Exception:
        # Если gen_random_uuid() не доступен, создаём расширение и используем uuid_generate_v4()
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        uuid_func = "uuid_generate_v4()"
    
    # Обновляем существующие записи
    connection.execute(text(f"""
        UPDATE supplier_profiles 
        SET id = {uuid_func}
        WHERE id IS NULL
    """))
    
    # Делаем id NOT NULL
    op.alter_column('supplier_profiles', 'id', nullable=False)
    
    # Удаляем старый primary key на supplier_id
    op.drop_constraint('supplier_profiles_pkey', 'supplier_profiles', type_='primary')
    
    # Создаём новый primary key на id
    op.create_primary_key('supplier_profiles_pkey', 'supplier_profiles', ['id'])
    
    # Добавляем unique constraint на supplier_id
    op.create_unique_constraint('uq_supplier_profile_supplier_id', 'supplier_profiles', ['supplier_id'])
    
    # Добавляем checklist_template_id в cases
    op.add_column('cases', sa.Column('checklist_template_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_cases_checklist_template_id',
        'cases', 'checklist_templates',
        ['checklist_template_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Удаляем checklist_template_id из cases
    op.drop_constraint('fk_cases_checklist_template_id', 'cases', type_='foreignkey')
    op.drop_column('cases', 'checklist_template_id')
    
    # Возвращаем supplier_id как primary key в supplier_profiles
    op.drop_constraint('uq_supplier_profile_supplier_id', 'supplier_profiles', type_='unique')
    op.drop_constraint('supplier_profiles_pkey', 'supplier_profiles', type_='primary')
    op.create_primary_key('supplier_profiles_pkey', 'supplier_profiles', ['supplier_id'])
    op.drop_column('supplier_profiles', 'id')

