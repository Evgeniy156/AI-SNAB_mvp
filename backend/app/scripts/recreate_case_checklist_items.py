"""Скрипт для пересоздания checklist items для существующих кейсов."""
import sys
import uuid
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.case import Case
from app.models.checklist_template import ChecklistTemplate
from app.models.case_checklist import CaseChecklistItem
from app.services.checklist import ensure_case_checklist


def recreate_case_checklist_items(db: Session, case_id: uuid.UUID | None = None) -> None:
    """
    Пересоздает checklist items для кейса(ов).
    
    Если case_id указан - пересоздает только для этого кейса.
    Если None - пересоздает для всех кейсов.
    """
    if case_id:
        cases = [db.query(Case).filter(Case.id == case_id).first()]
        if not cases[0]:
            print(f"Кейс {case_id} не найден")
            return
    else:
        cases = db.query(Case).all()
    
    print(f"Найдено кейсов: {len(cases)}")
    
    for case in cases:
        print(f"\nОбработка кейса: {case.code} ({case.id})")
        
        # Удаляем существующие checklist items
        existing_items = db.query(CaseChecklistItem).filter(
            CaseChecklistItem.case_id == case.id
        ).all()
        
        if existing_items:
            print(f"  Удаление существующих items: {len(existing_items)}")
            for item in existing_items:
                db.delete(item)
            db.flush()
        
        # Пересоздаем через ensure_case_checklist
        try:
            new_items = ensure_case_checklist(db, case.id)
            print(f"  Создано новых items: {len(new_items)}")
        except Exception as e:
            print(f"  ОШИБКА при создании items: {e}")
            db.rollback()
            continue
    
    db.commit()
    print(f"\nПересоздание завершено для {len(cases)} кейсов")


def main():
    """Точка входа для запуска скрипта."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Пересоздание checklist items для кейсов")
    parser.add_argument("--case-id", type=str, help="ID кейса (если не указан - обрабатываются все кейсы)")
    args = parser.parse_args()
    
    case_id = None
    if args.case_id:
        try:
            case_id = uuid.UUID(args.case_id)
        except ValueError:
            print(f"Неверный формат UUID: {args.case_id}")
            sys.exit(1)
    
    db = SessionLocal()
    try:
        recreate_case_checklist_items(db, case_id)
        print("\nПересоздание завершено успешно")
    except Exception as e:
        db.rollback()
        print(f"Ошибка пересоздания: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

