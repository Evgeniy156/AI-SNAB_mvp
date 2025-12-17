"""Скрипт для нормализации шаблонов чек-листа: очистка title от бланковых хвостов."""
import sys
import re
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.checklist_template import ChecklistTemplate, ChecklistTemplateItem
from app.models.case_checklist import CaseChecklistItem


def normalize_title(title: str) -> str:
    """
    Нормализует название пункта чек-листа: убирает бланковые хвосты.
    
    Удаляет:
    - №____ и любые комбинации пробелов/подчёркиваний после №
    - Хвосты " / от ..." или "/ от ..."
    - Хвосты "от «» ..." или "от «___» ..."
    - Длинные подчёркивания
    - Лишние пробелы
    """
    if not title:
        return title
    
    # Удаляем хвосты начиная с " / от" или "/ от"
    title_lower = title.lower()
    idx = -1
    for pattern in [" / от", "/ от", " /от", "/от"]:
        idx = title_lower.find(pattern)
        if idx > 0:
            title = title[:idx].strip()
            break
    
    # Если не нашли " / от", ищем просто " от" с кавычками
    if idx <= 0:
        for pattern in [" от «", " от \""]:
            idx = title_lower.find(pattern)
            if idx > 0:
                title = title[:idx].strip()
                break
    
    # Удаляем №________ и любые комбинации пробелов/подчёркиваний после №
    # Более агрессивная очистка: удаляем № и всё что после него до пробела или конца
    title = re.sub(r'\s*№\s*[_\s]+.*$', '', title)
    title = re.sub(r'\s*№\s*[_\s]+', '', title)
    
    # Удаляем длинные подчёркивания
    title = re.sub(r"_{3,}", "", title)
    
    # Убираем последовательности подчёркиваний длиной >= 2
    title = re.sub(r'_{2,}', '', title)
    
    # Убираем одиночные подчёркивания в начале/конце
    title = re.sub(r'^_+|_+$', '', title)
    
    # Удаляем точки в конце (если остались после очистки)
    title = re.sub(r'\.+$', '', title)
    
    # Схлопываем пробелы и strip()
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()
    
    return title


def should_remove_duplicate(title: str) -> bool:
    """
    Определяет, нужно ли удалить пункт как дубль.
    
    Удаляем:
    - "Служебная записка / от ..." (дубль с хвостом)
    - "Техническое задание" (короткий дубль, но оставляем с "(ЭСКИЗЫ)")
    - "Обоснование закупки" (убрать целиком)
    """
    if not title:
        return False
    
    title_lower = title.lower().strip()
    title_norm = normalize_title(title_lower)
    
    # Убираем "Служебная записка / от ..." (дубль с хвостом)
    if "служебная записка" in title_norm:
        if "/" in title_lower or "от «" in title_lower or " от " in title_lower:
            return True
    
    # Убираем короткий "Техническое задание", но оставляем с "(ЭСКИЗЫ)"
    if title_norm == "техническое задание" and "эскиз" not in title_lower:
        return True
    
    # Убираем "Обоснование закупки" целиком
    if title_norm == "обоснование закупки":
        return True
    
    return False


def normalize_template_items(db: Session, template_key: str = "PROCUREMENT_V1") -> None:
    """
    Нормализует все template items для указанного шаблона.
    
    Действия:
    1. Очищает title от бланковых хвостов
    2. Удаляет дубли
    3. Обновляет БД
    """
    template = db.query(ChecklistTemplate).filter(
        ChecklistTemplate.key == template_key
    ).first()
    
    if not template:
        print(f"Шаблон {template_key} не найден")
        return
    
    print(f"Найден шаблон: {template.key} ({template.name})")
    
    # Получаем все items шаблона
    items = db.query(ChecklistTemplateItem).filter(
        ChecklistTemplateItem.template_id == template.id
    ).all()
    
    print(f"Найдено пунктов: {len(items)}")
    
    items_to_delete = []
    items_to_update = []
    
    for item in items:
        original_title = item.title
        normalized_title = normalize_title(original_title)
        
        # Проверяем, нужно ли удалить как дубль
        if should_remove_duplicate(original_title):
            items_to_delete.append(item)
            print(f"  УДАЛЕНИЕ: {original_title[:60]}...")
            continue
        
        # Если title изменился, обновляем
        if normalized_title != original_title:
            item.title = normalized_title
            items_to_update.append(item)
            print(f"  ОБНОВЛЕНИЕ: '{original_title[:50]}...' -> '{normalized_title[:50]}...'")
    
    # Удаляем дубли (сначала удаляем связанные case_checklist_items, потом template_item)
    for item in items_to_delete:
        # Удаляем все связанные case_checklist_items
        case_items = db.query(CaseChecklistItem).filter(
            CaseChecklistItem.template_item_id == item.id
        ).all()
        if case_items:
            print(f"  Удаление связанных case_checklist_items: {len(case_items)}")
            for case_item in case_items:
                db.delete(case_item)
        # Удаляем template_item
        db.delete(item)
    
    # Коммитим изменения
    if items_to_delete or items_to_update:
        db.commit()
        print(f"\nОбработано:")
        print(f"  - Удалено дублей: {len(items_to_delete)}")
        print(f"  - Обновлено названий: {len(items_to_update)}")
    else:
        print("\nИзменений не требуется")


def main():
    """Точка входа для запуска скрипта нормализации."""
    db = SessionLocal()
    try:
        normalize_template_items(db)
        print("\nНормализация завершена успешно")
    except Exception as e:
        db.rollback()
        print(f"Ошибка нормализации: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

