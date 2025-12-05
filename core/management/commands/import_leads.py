import csv
import uuid
import os
from django.core.management.base import BaseCommand
from core.models import Lead, LeadStatus

class Command(BaseCommand):
    help = 'Финальный импорт лидов (NSRE)'

    def handle(self, *args, **kwargs):
        file_path = 'leads.csv'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'❌ Файл {file_path} не найден!'))
            return

        self.stdout.write(f'🚀 Начинаем импорт...')

        with open(file_path, 'r', encoding='utf-8-sig') as file:
            # Используем разделитель "точка с запятой", как показала разведка
            reader = csv.reader(file, delimiter=';')
            
            # --- ПРОПУСК ЗАГОЛОВКОВ ---
            # Судя по твоему отчету, данные начинаются с 3-й строки (индекс 2)
            # Пропускаем строку 0 (пустую) и строку 1 (заголовки)
            try:
                next(reader) 
                next(reader)
            except StopIteration:
                self.stdout.write("Файл пустой!")
                return

            count_new = 0
            count_skip = 0

            for i, row in enumerate(reader):
                # Пропускаем пустые строки
                if not row or len(row) < 3: 
                    continue
                
                try:
                    # --- ИЗВЛЕЧЕНИЕ ДАННЫХ ---
                    # [1] = Name
                    # [2] = Tel number
                    # [4] = Level (может быть пустым, поэтому используем try/except для индекса)
                    
                    name = row[1].strip()
                    phone_raw = row[2].strip()
                    
                    # Безопасно достаем уровень (если колонки нет, будет пустая строка)
                    level = row[4].strip() if len(row) > 4 else ""

                    # --- ОЧИСТКА ---
                    # Убираем пробелы из телефона (90 937 -> 90937)
                    phone = phone_raw.replace(" ", "").replace("-", "")
                    
                    # Если имени или телефона нет - пропускаем
                    if len(phone) < 5:
                        continue
                    if not name:
                        name = "Без имени"

                    # Генерируем ID
                    fake_id = f"import_{uuid.uuid4().hex[:8]}"
                    
                    # Комментарий с уровнем
                    comment = "Импорт из Excel."
                    if level:
                        comment += f"\n📚 Уровень: {level}"

                    # --- ЗАПИСЬ В БАЗУ ---
                    lead, created = Lead.objects.get_or_create(
                        phone=phone,
                        defaults={
                            'first_name': name,
                            'telegram_id': fake_id,
                            'source': 'Import',
                            'status': LeadStatus.NEW,
                            'manager_comment': comment
                        }
                    )

                    if created:
                        count_new += 1
                        self.stdout.write(f"✅ {name} ({level})")
                    else:
                        count_skip += 1

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️ Ошибка в строке {i}: {e}"))
                    continue

        self.stdout.write(self.style.SUCCESS(f'\n🎉 ГОТОВО!'))
        self.stdout.write(f'Добавлено новых: {count_new}')
        self.stdout.write(f'Пропущено (уже были): {count_skip}')