"""add document fields and ensure bucket

Revision ID: 4fb8f520f189
Revises: b2c3d4e5f6a7
Create Date: 2025-12-12 20:36:22.969972

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4fb8f520f189'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Переименовываем filename в original_filename (если колонка существует)
    try:
        op.alter_column('documents', 'filename', new_column_name='original_filename', existing_type=sa.String(length=255), existing_nullable=False)
    except Exception:
        # Колонка уже переименована или не существует
        pass
    
    # Добавляем storage_bucket (если не существует)
    try:
        op.add_column('documents', sa.Column('storage_bucket', sa.String(length=100), server_default='aisnab-files', nullable=False))
    except Exception:
        # Колонка уже существует
        pass
    
    # Делаем storage_key NOT NULL (если был nullable)
    try:
        op.alter_column('documents', 'storage_key', existing_type=sa.String(length=500), nullable=False)
    except Exception:
        pass
    
    # Добавляем новые поля
    try:
        op.add_column('documents', sa.Column('content_type', sa.String(length=100), nullable=True))
    except Exception:
        pass
    
    try:
        op.add_column('documents', sa.Column('size_bytes', sa.Integer(), nullable=True))
    except Exception:
        pass
    
    try:
        op.add_column('documents', sa.Column('error_message', sa.String(length=500), nullable=True))
    except Exception:
        pass
    
    # Изменяем default для status с 'NEW'/'UPLOADED' на 'IN_PROGRESS'
    # Обновляем существующие записи
    op.execute("UPDATE documents SET status = 'DONE' WHERE status IN ('NEW', 'UPLOADED')")
    # Меняем default
    op.alter_column('documents', 'status', server_default='IN_PROGRESS', existing_type=sa.String(length=50), existing_nullable=False)
    
    # Добавляем индексы
    try:
        op.create_index('ix_documents_case_id', 'documents', ['case_id'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_documents_category_id', 'documents', ['category_id'])
    except Exception:
        pass


def downgrade():
    # Убираем индексы
    try:
        op.drop_index('ix_documents_category_id', table_name='documents')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_documents_case_id', table_name='documents')
    except Exception:
        pass
    
    # Убираем новые поля
    try:
        op.drop_column('documents', 'error_message')
    except Exception:
        pass
    
    try:
        op.drop_column('documents', 'size_bytes')
    except Exception:
        pass
    
    try:
        op.drop_column('documents', 'content_type')
    except Exception:
        pass
    
    # Возвращаем default для status
    op.execute("UPDATE documents SET status = 'NEW' WHERE status IN ('DONE', 'IN_PROGRESS')")
    op.alter_column('documents', 'status', server_default='NEW', existing_type=sa.String(length=50), existing_nullable=False)
    
    # Убираем storage_bucket
    try:
        op.drop_column('documents', 'storage_bucket')
    except Exception:
        pass
    
    # Возвращаем storage_key nullable
    try:
        op.alter_column('documents', 'storage_key', existing_type=sa.String(length=500), nullable=True)
    except Exception:
        pass
    
    # Возвращаем original_filename в filename
    try:
        op.alter_column('documents', 'original_filename', new_column_name='filename', existing_type=sa.String(length=255), existing_nullable=False)
    except Exception:
        pass

