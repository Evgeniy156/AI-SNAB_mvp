"""add document categories

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-12 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Создание таблицы document_categories
    op.create_table(
        'document_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(length=50), nullable=False, unique=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Добавление колонки category_id в documents (пока nullable)
    op.add_column('documents', sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Создание FK constraint
    op.create_foreign_key(
        'fk_documents_category_id',
        'documents', 'document_categories',
        ['category_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    # Создание дефолтной категории OTHER
    op.execute("""
        INSERT INTO document_categories (id, key, name, is_active, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'OTHER',
            'Прочее',
            true,
            NOW(),
            NOW()
        )
    """)
    
    # Получаем ID категории OTHER
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM document_categories WHERE key = 'OTHER' LIMIT 1"))
    other_category_id = result.scalar()
    
    # Проставляем category_id=OTHER всем существующим документам
    if other_category_id:
        op.execute(f"""
            UPDATE documents
            SET category_id = '{other_category_id}'
            WHERE category_id IS NULL
        """)
    
    # Делаем category_id NOT NULL
    op.alter_column('documents', 'category_id', nullable=False)


def downgrade():
    # Удаляем NOT NULL constraint
    op.alter_column('documents', 'category_id', nullable=True)
    
    # Удаляем FK constraint
    op.drop_constraint('fk_documents_category_id', 'documents', type_='foreignkey')
    
    # Удаляем колонку category_id
    op.drop_column('documents', 'category_id')
    
    # Удаляем таблицу document_categories
    op.drop_table('document_categories')

