from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import User

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
    Лиды - потенциальные клиенты.
    """
    first_name = models.CharField("Имя / Никнейм", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100, blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    telegram_id = models.CharField("Telegram ID", max_length=50, blank=True, unique=True)
    telegram_username = models.CharField("Telegram Username", max_length=100, blank=True)
    
    status = models.CharField("Статус", max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW)
    source = models.CharField("Источник", max_length=100, blank=True)
    manager_comment = models.TextField("Комментарий менеджера", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Лид (Заявка)"
        verbose_name_plural = "Лиды (Заявки)"

    def __str__(self):
        contact = self.phone if self.phone else f"@{self.telegram_username}"
        return f"{self.first_name} | {contact}"


class Teacher(models.Model):
    full_name = models.CharField("ФИО Преподавателя", max_length=150)
    phone = models.CharField("Телефон", max_length=20)
    is_active = models.BooleanField("Работает сейчас", default=True)

    class Meta:
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"

    def __str__(self):
        return self.full_name


class Group(models.Model):
    name = models.CharField("Название группы", max_length=100)
    level = models.CharField("Уровень HSK", max_length=10, choices=HSKLevel.choices)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, verbose_name="Преподаватель")
    days_description = models.CharField("Расписание", max_length=100)
    start_date = models.DateField("Дата старта", default=now)
    is_active = models.BooleanField("Группа активна", default=True)

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"

    def __str__(self):
        return f"{self.name} ({self.days_description})"


class Student(models.Model):
    STATUS_CHOICES = [
        ('active', '🟢 Активен'),
        ('paused', '🟡 Заморозка'),
        ('banned', '🔴 Исключен (Много прогулов)'),
    ]

    lead = models.OneToOneField(Lead, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Из какого лида")
    full_name = models.CharField("ФИО", max_length=150)
    phone = models.CharField("Телефон", max_length=20)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Группа", related_name="students")
    student_status = models.CharField("Статус студента", max_length=20, choices=STATUS_CHOICES, default='active')
    balance = models.IntegerField("Остаток уроков", default=0)
    total_paid = models.DecimalField("Всего денег принес", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"

    def __str__(self):
        return f"{self.full_name} ({self.get_student_status_display()})"


class Lesson(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="Группа", related_name="lessons")
    date = models.DateField("Дата урока", default=now)
    topic = models.CharField("Тема урока", max_length=200, blank=True)
    
    class Meta:
        verbose_name = "Проведенный урок"
        verbose_name_plural = "Журнал уроков"
        ordering = ['-date']

    def __str__(self):
        return f"{self.group.name} - {self.date}"


class Attendance(models.Model):
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
        unique_together = ('lesson', 'student')

    def __str__(self):
        return f"{self.student} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            if self.status in ['present', 'absent']:
                self.student.balance -= 1
                self.student.save()

            if self.status == 'absent':
                absent_count = Attendance.objects.filter(student=self.student, status='absent').count()
                if absent_count >= 3:
                    self.student.student_status = 'banned'
                    self.student.save()


class Tariff(models.Model):
    name = models.CharField("Название тарифа", max_length=100)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=0)
    lessons_count = models.IntegerField("Количество уроков")

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"

    def __str__(self):
        return f"{self.name} ({self.price})"


class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Студент", related_name="payments")
    tariff = models.ForeignKey(Tariff, on_delete=models.SET_NULL, null=True, verbose_name="Купленный тариф")
    date = models.DateTimeField("Дата и время", default=now)
    amount = models.DecimalField("Сумма оплаты", max_digits=10, decimal_places=0)
    comment = models.TextField("Комментарий", blank=True)

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "История оплат"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} - {self.amount}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.amount and self.tariff:
            self.amount = self.tariff.price

        super().save(*args, **kwargs)
        
        if is_new and self.tariff:
            self.student.balance += self.tariff.lessons_count
            self.student.total_paid += self.amount
            if self.student.student_status != 'active':
                self.student.student_status = 'active'
            self.student.save()


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', '🟢 Низкий'),
        ('medium', '🟡 Средний'),
        ('high', '🔴 Высокий (Срочно!)'),
    ]
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('done', '✅ Выполнено'),
    ]

    title = models.CharField("Что сделать?", max_length=200)
    description = models.TextField("Подробное описание", blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Исполнитель", related_name="tasks")
    deadline = models.DateTimeField("Крайний срок", null=True, blank=True)
    priority = models.CharField("Важность", max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи сотрудникам"
        ordering = ['status', '-priority']

    def __str__(self):
        return f"{self.title} ({self.assigned_to})"


# --- ВОТ ОН, НАШ НОВЫЙ КЛАСС ДЛЯ ЧАТА ---
class ChatMessage(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='messages')
    text = models.TextField("Текст сообщения")
    is_from_manager = models.BooleanField("От менеджера?", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"

    def __str__(self):
        direction = "➡️ Менеджер"