import csv
import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Показывает структуру CSV файла'

    def handle(self, *args, **kwargs):
        # Имя файла
        file_path = 'leads.csv'

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'❌ Файл {file_path} не найден!'))
            return

        self.stdout.write(f'🔍 Анализируем файл: {file_path}...')

        # Список кодировок для перебора
        encodings = ['utf-8-sig', 'gb18030', 'cp1251', 'utf-8']
        
        for enc in encodings:
            try:
                print(f"\n--- Пробуем кодировку: {enc} ---")
                with open(file_path, 'r', encoding=enc) as file:
                    # Читаем кусочек для определения разделителя
                    sample = file.read(1024)
                    file.seek(0)
                    
                    # Пытаемся угадать разделитель (; или ,)
                    try:
                        dialect = csv.Sniffer().sniff(sample)
                        delimiter = dialect.delimiter
                    except:
                        delimiter = ',' # Если не угадали, пробуем запятую
                    
                    print(f"Разделитель: '{delimiter}'")

                    reader = csv.reader(file, delimiter=delimiter)
                    
                    # Выводим первые 3 строки
                    printed_rows = 0
                    for i, row in enumerate(reader):
                        if not row: continue # Пропуск пустых
                        
                        print(f"\n📝 Строка №{i}:")
                        for idx, value in enumerate(row):
                            print(f"   [{idx}] = {value}")
                        
                        printed_rows += 1
                        if printed_rows >= 3:
                            break
                
                print(f"\n✅ Успешно прочитано в кодировке {enc}!")
                break # Если получилось - выходим из цикла

            except Exception as e:
                print(f"❌ Не подошла кодировка {enc}: {e}")