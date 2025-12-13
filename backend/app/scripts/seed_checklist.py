"""Seed скрипт для создания шаблона чек-листа из Word документа."""
import sys
import os
import re
from pathlib import Path
from docx import Document
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.checklist_template import ChecklistTemplate, ChecklistTemplateItem


def parse_docx(file_path: Path) -> list[dict]:
    """
    Парсит Word документ и извлекает пункты чек-листа.
    
    Возвращает список словарей с ключами:
    - section: str (например "I. Подготовительный этап")
    - group_title: str | None (например "1. Основание закупки")
    - title: str (текст пункта после checkbox символов)
    - is_required: bool
    """
    doc = Document(file_path)
    items = []
    current_section = None
    current_group = None
    
    # Символы checkbox: ☐ (пустой), ☑ (отмеченный), ▢ (пустой квадрат)
    checkbox_pattern = re.compile(r'^[☐☑▢]\s*')
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        
        # Определяем секцию по римским цифрам I, II, III, IV, V, VI
        section_match = re.match(r'^([IVX]+)\.\s*(.+)$', text)
        if section_match:
            current_section = text
            current_group = None
            continue
        
        # Определяем группу по арабским цифрам (1., 2., 3., и т.д.)
        group_match = re.match(r'^(\d+)\.\s*(.+)$', text)
        if group_match and current_section:
            current_group = text
            continue
        
        # Определяем пункт чек-листа по checkbox символам
        if checkbox_pattern.match(text) and current_section:
            # Убираем checkbox символы из начала
            title = checkbox_pattern.sub('', text).strip()
            
            # Определяем обязательность (если есть маркер обязательности или по умолчанию)
            is_required = True  # По умолчанию все обязательные
            
            items.append({
                'section': current_section,
                'group_title': current_group,
                'title': title,
                'is_required': is_required
            })
    
    return items


def seed_checklist(db: Session, docx_path: Path | None = None) -> None:
    """
    Создает или обновляет шаблон чек-листа PROCUREMENT_V1 из Word документа.
    
    Идемпотентно: если template уже существует, обновляет его метаданные,
    но не дублирует items (проверка по (template_id, title) + sort_order).
    """
    if docx_path is None:
        # Путь относительно директории app (где находится скрипт)
        # __file__ = backend/app/scripts/seed_checklist.py
        # parent.parent = backend/app
        app_dir = Path(__file__).parent.parent
        docx_path = app_dir / "docs" / "checklist_procurement.docx"
    
    if not docx_path.exists():
        print(f"WARNING: Word файл не найден: {docx_path}")
        print("Создаю пустой шаблон PROCUREMENT_V1")
        # Создаем пустой шаблон, если файла нет
        template = db.query(ChecklistTemplate).filter(
            ChecklistTemplate.key == "PROCUREMENT_V1"
        ).first()
        
        if not template:
            template = ChecklistTemplate(
                key="PROCUREMENT_V1",
                name="Чек-лист отдела кооперации",
                is_active=True,
                is_default=True
            )
            db.add(template)
            db.commit()
            print(f"Создан пустой шаблон: {template.key}")
        else:
            print(f"Шаблон уже существует: {template.key}")
        return
    
    # Парсим Word документ
    print(f"Парсинг Word документа: {docx_path}")
    items_data = parse_docx(docx_path)
    print(f"Найдено пунктов: {len(items_data)}")
    
    # Находим или создаем template
    template = db.query(ChecklistTemplate).filter(
        ChecklistTemplate.key == "PROCUREMENT_V1"
    ).first()
    
    if template:
        # Обновляем метаданные
        template.name = "Чек-лист отдела кооперации"
        template.is_active = True
        template.is_default = True
        print(f"Обновлен существующий шаблон: {template.key}")
    else:
        template = ChecklistTemplate(
            key="PROCUREMENT_V1",
            name="Чек-лист отдела кооперации",
            is_active=True,
            is_default=True
        )
        db.add(template)
        db.flush()  # Получаем ID
        print(f"Создан новый шаблон: {template.key}")
    
    # Создаем или обновляем items
    existing_items = {
        (item.template_id, item.title): item
        for item in db.query(ChecklistTemplateItem).filter(
            ChecklistTemplateItem.template_id == template.id
        ).all()
    }
    
    created_count = 0
    updated_count = 0
    
    for sort_order, item_data in enumerate(items_data, start=1):
        key = (template.id, item_data['title'])
        
        if key in existing_items:
            # Обновляем существующий item
            item = existing_items[key]
            item.section = item_data['section']
            item.group_title = item_data['group_title']
            item.is_required = item_data['is_required']
            item.sort_order = sort_order
            updated_count += 1
        else:
            # Создаем новый item
            item = ChecklistTemplateItem(
                template_id=template.id,
                section=item_data['section'],
                group_title=item_data['group_title'],
                title=item_data['title'],
                is_required=item_data['is_required'],
                sort_order=sort_order
            )
            db.add(item)
            created_count += 1
    
    db.commit()
    print(f"Создано пунктов: {created_count}, обновлено: {updated_count}, всего: {len(items_data)}")


def main():
    """Точка входа для запуска seed скрипта."""
    db = SessionLocal()
    try:
        seed_checklist(db)
        print("Seed checklist завершен успешно")
    except Exception as e:
        db.rollback()
        print(f"Ошибка seed checklist: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

