from django.db import models
from django.utils import timezone

# --- СПРАВОЧНИКИ ---

class HSKLevel(models.TextChoices):
    HSK1 = 'HSK1', 'HSK 1 (Начальный)'
    HSK2 = 'HSK2', 'HSK 2'
    HSK3 = 'HSK3', 'HSK 3 (Средний)'
    HSK4 = 'HSK4', 'HSK 4'
    HSK5 = 'HSK5', 'HSK 5 (Продвинутый)'
    HSK6 = 'HSK6', 'HSK 6'

class LeadStatus(models.TextChoices):
    NEW = 'new', '🔥 Новый'
    IN_PROGRESS = 'process', '⏳ В обработке'
    WAITING_PAYMENT = 'payment', '💰 Ждем оплату'
    WON = 'won', '✅ Записан в группу'
    LOST = 'lost', '❌ Отказ'

# --- ОСНОВНЫЕ ТАБЛИЦЫ ---

class Lead(models.Model):
    """
    Лиды - потенциальные клиенты (звонки, заявки).
    """
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100, blank=True)
    phone = models.CharField("Телефон", max_length=20)
    status = models.CharField(
        "Статус", 
        max_length=20, 
        choices=LeadStatus.choices, 
        default=LeadStatus.NEW
    )
    source = models.CharField("Источник (откуда узнал)", max_length=100, blank=True)
    manager_comment = models.TextField("Комментарий менеджера", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Лид (Заявка)"
        verbose_name_plural = "Лиды (Заявки)"

    def __str__(self):
        return f"{self.first_name} {self.phone} ({self.get_status_display()})"


class Teacher(models.Model):
    """
    Преподаватели
    """
    full_name = models.CharField("ФИО Преподавателя", max_length=150)
    phone = models.CharField("Телефон", max_length=20)
    is_active = models.BooleanField("Работает сейчас", default=True)

    class Meta:
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"

    def __str__(self):
        return self.full_name


class Group(models.Model):
    """
    Учебные группы (фиксированный состав)
    """
    name = models.CharField("Название группы", max_length=100, help_text="Например: Группа HSK-1 Вечер")
    level = models.CharField("Уровень HSK", max_length=10, choices=HSKLevel.choices)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, verbose_name="Преподаватель")
    days_description = models.CharField("Расписание", max_length=100, help_text="Например: Пн/Ср 19:00")
    start_date = models.DateField("Дата старта", default=timezone.now)
    is_active = models.BooleanField("Группа активна", default=True)

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self):
        return f"{self.name} ({self.days_description})"


class Student(models.Model):
    """
    Ученики - те, кто уже учится.
    """
    # Варианты статусов студента
    STATUS_CHOICES = [
        ('active', '🟢 Активен'),
        ('paused', '🟡 Заморозка'),
        ('banned', '🔴 Исключен (Много прогулов)'),
    ]

    lead = models.OneToOneField(Lead, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Из какого лида")
    full_name = models.CharField("ФИО", max_length=150)
    phone = models.CharField("Телефон", max_length=20)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Группа", related_name="students")
    
    # Вот это новое поле:
    student_status = models.CharField("Статус студента", max_length=20, choices=STATUS_CHOICES, default='active')
    
    balance = models.IntegerField("Остаток уроков", default=0)
    total_paid = models.DecimalField("Всего денег принес", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"

    def __str__(self):
        return f"{self.full_name} ({self.get_student_status_display()})"

    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"

    def __str__(self):
        return f"{self.full_name} (Баланс: {self.balance})"
    
    # --- ЖУРНАЛ ПОСЕЩАЕМОСТИ ---

class Lesson(models.Model):
    """
    Конкретный проведенный урок.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="Группа", related_name="lessons")
    date = models.DateField("Дата урока", default=timezone.now)
    topic = models.CharField("Тема урока", max_length=200, blank=True)
    
    class Meta:
        verbose_name = "Проведенный урок"
        verbose_name_plural = "Журнал уроков"
        ordering = ['-date']

    def __str__(self):
        return f"{self.group.name} - {self.date}"


class Attendance(models.Model):
    """
    Отметка конкретного студента на конкретном уроке.
    """
    STATUS_CHOICES = [
        ('present', '✅ Присутствовал (-1 урок)'),
        ('absent', '❌ Прогул (-1 урок)'),
        ('excused', '🏥 Уважительная причина (0 уроков)'),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Студент")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='present')

    class Meta:
        verbose_name = "Отметка"
        verbose_name_plural = "Отметки"
        unique_together = ('lesson', 'student') # Защита от дублей

    def __str__(self):
        return f"{self.student} - {self.get_status_display()}"
    
    # --- ЛОГИКА АВТОМАТИЗАЦИИ ---
    def save(self, *args, **kwargs):
        is_new = self.pk is None # Проверяем, новая ли это запись
        
        super().save(*args, **kwargs) # Сохраняем в базу
        
        if is_new:
            # 1. Списание баланса (если был или прогулял)
            if self.status in ['present', 'absent']:
                self.student.balance -= 1
                self.student.save()

            # 2. Проверка на бан (если 3-й прогул)
            if self.status == 'absent':
                # Считаем все прогулы этого студента
                absent_count = Attendance.objects.filter(student=self.student, status='absent').count()
                
                if absent_count >= 3:
                    self.student.student_status = 'banned' # Меняем статус на "Исключен"
                    self.student.save()

 # --- ФИНАНСОВЫЙ БЛОК ---

class Tariff(models.Model):
    """
    Варианты абонементов (Товарная линейка)
    """
    name = models.CharField("Название тарифа", max_length=100, help_text="Например: Абонемент 8 занятий")
    price = models.DecimalField("Цена", max_digits=10, decimal_places=0)
    lessons_count = models.IntegerField("Количество уроков")

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"

    def __str__(self):
        return f"{self.name} ({self.price} сум)"


class Payment(models.Model):
    """
    История оплат.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Студент", related_name="payments")
    tariff = models.ForeignKey(Tariff, on_delete=models.SET_NULL, null=True, verbose_name="Купленный тариф")
    date = models.DateTimeField("Дата и время", default=timezone.now)
    amount = models.DecimalField("Сумма оплаты", max_digits=10, decimal_places=0, help_text="Может отличаться от цены тарифа, если была скидка")
    comment = models.TextField("Комментарий", blank=True)

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "История оплат"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} - {self.amount}"

    # --- МАГИЯ: НАЧИСЛЕНИЕ БАЛАНСА ---
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Если менеджер не ввел сумму вручную, подставляем цену тарифа
        if not self.amount and self.tariff:
            self.amount = self.tariff.price

        super().save(*args, **kwargs)
        
        if is_new and self.tariff:
            # 1. Добавляем уроки студенту
            self.student.balance += self.tariff.lessons_count
            
            # 2. Увеличиваем LTV (жизненную ценность клиента - сколько всего денег принес)
            self.student.total_paid += self.amount
            
            # 3. Если студент был "Исключен" или "Заморожен", возвращаем его в строй
            if self.student.student_status != 'active':
                self.student.student_status = 'active'
            
            self.student.save()                   