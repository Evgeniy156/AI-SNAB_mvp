"""Seed script для создания демо-данных поставщиков, кейсов и категорий документов."""
import sys
from datetime import datetime, date, timedelta
from app.db.session import SessionLocal
from app.models.supplier import Supplier
from app.models.case import Case
from app.models.document_category import DocumentCategory
from app.models.supplier_profile import (
    SupplierProfile,
    OkvedCode,
    SupplierOkved,
    SupplierEquipment,
    SupplierCertificate
)
from app.models.procurement import (
    CaseCandidate,
    RfqRequest,
    CommercialOffer,
    SupplierSecurityReview
)
from app.services.supplier_profile import (
    get_or_create_supplier_profile,
    set_supplier_okved,
    add_supplier_equipment,
    add_supplier_certificate
)
from app.services.procurement import (
    add_candidate_to_case,
    recompute_case_pricing
)
from app.scripts.seed_checklist import seed_checklist


def main():
    db = SessionLocal()
    try:
        print("Seed started")

        # Создаем поставщиков, если их нет
        supplier_count = db.query(Supplier).count()
        if supplier_count == 0:
            suppliers = [
                Supplier(name="ООО Поставщик А"),
                Supplier(name="ООО Поставщик Б"),
                Supplier(name="АО Поставщик В"),
            ]
            db.add_all(suppliers)
            db.commit()
            print(f"Suppliers created: {len(suppliers)}")
        else:
            suppliers = db.query(Supplier).all()
            print(f"Suppliers exist: {supplier_count}")

        # Создаем кейсы, если их нет
        case_count = db.query(Case).count()
        if case_count == 0 and len(suppliers) > 0:
            cases = [
                Case(code="CASE-2025-001", title="Кейс закупки №1", supplier_id=suppliers[0].id),
                Case(code="CASE-2025-002", title="Кейс закупки №2", supplier_id=suppliers[1].id if len(suppliers) > 1 else None),
                Case(code="CASE-2025-003", title="Кейс закупки №3", supplier_id=suppliers[2].id if len(suppliers) > 2 else None),
            ]
            db.add_all(cases)
            db.commit()
            print(f"Cases created: {len(cases)}")
        else:
            print(f"Cases exist: {case_count}")

        # Создаем категории документов (идемпотентно по key)
        categories_data = [
            {"key": "KP", "name": "Коммерческое предложение"},
            {"key": "EMAIL_SCREEN", "name": "Скриншот email"},
            {"key": "EMAIL_EML", "name": "Email файл (.eml)"},
            {"key": "LETTER", "name": "Письмо"},
            {"key": "REFUSAL", "name": "Отказ"},
            {"key": "TZ", "name": "Техническое задание"},
            {"key": "CONTRACT", "name": "Договор"},
            {"key": "CERT_QUALITY", "name": "Сертификат качества"},
            {"key": "CERT_ISO", "name": "Сертификат ISO"},
            {"key": "FOUNDING_DOCS", "name": "Учредительные документы"},
            {"key": "OTHER", "name": "Прочее"},
            # Категории документов поставщиков
            {"key": "SUPPLIER_CHARTER", "name": "Устав/учредительные документы"},
            {"key": "SUPPLIER_EGRUL", "name": "Выписка ЕГРЮЛ"},
            {"key": "SUPPLIER_POWER_OF_ATTORNEY", "name": "Доверенность"},
            {"key": "SUPPLIER_QMS_CERT", "name": "Сертификаты СМК"},
            {"key": "SUPPLIER_OKVED_PROOF", "name": "ОКВЭД подтверждение"},
            {"key": "SUPPLIER_CAPACITY_PROOF", "name": "Мощности/оборудование"},
            {"key": "SUPPLIER_HEADCOUNT_PROOF", "name": "Персонал/штат"},
            {"key": "SUPPLIER_GOZ_PROOF", "name": "ГОЗ/допуски"},
            {"key": "SUPPLIER_REFERENCES", "name": "Референсы/опыт"},
            {"key": "SUPPLIER_BANK_DETAILS", "name": "Реквизиты банка"},
            # Категории документов для закупки
            {"key": "RFQ_EVIDENCE", "name": "Подтверждение отправки запроса КП"},
            {"key": "SB_CONCLUSION", "name": "Заключение СБ"},
        ]
        created_count = 0
        for cat_data in categories_data:
            existing = db.query(DocumentCategory).filter(DocumentCategory.key == cat_data["key"]).first()
            if not existing:
                category = DocumentCategory(**cat_data)
                db.add(category)
                created_count += 1
        if created_count > 0:
            db.commit()
            print(f"Categories created: {created_count}")
        else:
            print(f"Categories seed skipped: all exist")

        # Seed чек-листа
        print("\nSeeding checklist...")
        seed_checklist(db)

        # Seed демо-данных профилей поставщиков
        print("\nSeeding supplier profiles...")
        if len(suppliers) > 0:
            # Профиль для первого поставщика
            profile1 = get_or_create_supplier_profile(db, suppliers[0].id)
            profile1.headcount_total = 150
            profile1.headcount_engineering = 30
            profile1.headcount_production = 100
            profile1.headcount_quality = 20
            profile1.has_qms = True
            profile1.qms_standards = "ISO 9001:2015"
            profile1.works_with_goz = True
            profile1.executed_contracts_count = 25
            profile1.business_description = "Производство металлообрабатывающего оборудования"
            profile1.main_products_services = "Станки, прессы, инструмент"
            db.commit()
            
            # ОКВЭД для первого поставщика
            set_supplier_okved(db, suppliers[0].id, ["25.11", "25.12", "28.41"])
            
            # Оборудование для первого поставщика
            add_supplier_equipment(db, suppliers[0].id, "Токарный станок", "CNC-500", 5, "С ЧПУ")
            add_supplier_equipment(db, suppliers[0].id, "Фрезерный станок", "FM-300", 3)
            
            # Сертификат для первого поставщика
            add_supplier_certificate(
                db, suppliers[0].id, "ISO 9001:2015", "ISO-2023-001",
                "Орган по сертификации", "2023-01-01", "2026-01-01",
                "Система менеджмента качества"
            )
            
            print(f"Profile created for supplier: {suppliers[0].name}")
        
        if len(suppliers) > 1:
            # Профиль для второго поставщика
            profile2 = get_or_create_supplier_profile(db, suppliers[1].id)
            profile2.headcount_total = 80
            profile2.headcount_engineering = 15
            profile2.headcount_production = 50
            profile2.has_qms = False
            profile2.works_with_goz = False
            profile2.executed_contracts_count = 10
            db.commit()
            
            set_supplier_okved(db, suppliers[1].id, ["25.20", "25.30"])
            print(f"Profile created for supplier: {suppliers[1].name}")

        # Seed демо-данных закупки
        print("\nSeeding procurement data...")
        if case_count > 0:
            # Берём первый кейс
            first_case = db.query(Case).first()
            
            # Обновляем параметры закупки
            first_case.procurement_type = "GOODS_SUPPLY"
            first_case.subject = "Закупка металлообрабатывающего оборудования"
            first_case.initiator_department = "Отдел закупок"
            first_case.planned_deadline = date.today() + timedelta(days=90)
            db.commit()
            
            # Добавляем 3 кандидатов
            if len(suppliers) >= 2:
                # Кандидат 1: существующий поставщик
                candidate1 = add_candidate_to_case(
                    db, first_case.id,
                    supplier_id=suppliers[0].id
                )
                
                # Кандидат 2: существующий поставщик
                candidate2 = add_candidate_to_case(
                    db, first_case.id,
                    supplier_id=suppliers[1].id
                )
                
                # Кандидат 3: организация без supplier
                candidate3 = add_candidate_to_case(
                    db, first_case.id,
                    org_name="ООО Новый Поставщик",
                    inn="1234567890",
                    contact_email="info@new-supplier.ru",
                    contact_phone="+7 (495) 123-45-67"
                )
                
                # Добавляем 3 КП (цены так, чтобы coeff был < 0.33)
                from decimal import Decimal
                offer1 = CommercialOffer(
                    case_id=first_case.id,
                    candidate_id=candidate1.id,
                    supplier_id=suppliers[0].id,
                    price_total=Decimal("1000000.00"),
                    lead_time_days=30
                )
                offer2 = CommercialOffer(
                    case_id=first_case.id,
                    candidate_id=candidate2.id,
                    supplier_id=suppliers[1].id,
                    price_total=Decimal("1050000.00"),
                    lead_time_days=35
                )
                offer3 = CommercialOffer(
                    case_id=first_case.id,
                    candidate_id=candidate3.id,
                    supplier_id=None,
                    price_total=Decimal("1020000.00"),
                    lead_time_days=32
                )
                db.add_all([offer1, offer2, offer3])
                db.commit()
                
                # Пересчитываем НМЦ
                recompute_case_pricing(db, first_case.id)
                
                # Создаём проверку СБ для первого поставщика (APPROVED)
                security_review = SupplierSecurityReview(
                    case_id=first_case.id,
                    supplier_id=suppliers[0].id,
                    status="APPROVED",
                    reviewed_at=datetime.utcnow(),
                    comment="Проверка пройдена успешно"
                )
                db.add(security_review)
                db.commit()
                
                print(f"Procurement data created for case: {first_case.code}")

        print("Seed done")
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

