from django.contrib import admin
from django.contrib.auth.models import Group as DjangoGroup
from django.utils.html import format_html
from django.urls import reverse
from .models import Lead, Student, Teacher, Group, Lesson, Attendance, Tariff, Payment, Task, ChatMessage

# --- ВНУТРЕННИЕ ТАБЛИЦЫ (INLINES) ---

class AttendanceInline(admin.TabularInline):
    """Позволяет отмечать студентов внутри страницы Урока"""
    model = Attendance
    extra = 0
    autocomplete_fields = ['student']
    min_num = 1

class PaymentInline(admin.TabularInline):
    """История оплат внутри студента"""
    model = Payment
    extra = 0
    readonly_fields = ('date', 'amount', 'tariff')
    can_delete = False

# --- ОСНОВНЫЕ РАЗДЕЛЫ ---

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    # Добавили open_chat_link в список
    list_display = ('first_name', 'phone', 'status', 'source', 'open_chat_link')
    list_filter = ('status', 'source')
    search_fields = ('first_name', 'phone', 'telegram_username')
    list_editable = ('status',)

    # Кнопка для перехода в чат
    def open_chat_link(self, obj):
        url = reverse('chat_dashboard', args=[obj.id]) 
        return format_html('<a class="button" href="{}" style="background-color:#28a745; color:white; padding:5px 10px; border-radius:5px;">💬 Чат</a>', url)
    
    open_chat_link.short_description = "Переписка"

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'group', 'balance', 'student_status')
    list_filter = ('group', 'student_status')
    search_fields = ('full_name', 'phone')
    inlines = [PaymentInline] # Видно оплаты внутри студента

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'is_active')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'teacher', 'days_description', 'count_students')
    def count_students(self, obj):
        return obj.students.count()
    count_students.short_description = "Учеников"

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('group', 'date', 'topic', 'students_checked')
    list_filter = ('group', 'date')
    date_hierarchy = 'date'
    inlines = [AttendanceInline] # Журнал посещаемости

    def students_checked(self, obj):
        return obj.attendance_records.count()
    students_checked.short_description = "Отмечено чел."

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name', 'lessons_count', 'price')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'tariff', 'amount', 'date')
    list_filter = ('date', 'tariff')
    search_fields = ('student__full_name',)
    autocomplete_fields = ['student']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'deadline', 'priority', 'status')
    list_filter = ('status', 'priority', 'assigned_to')
    search_fields = ('title',)
    list_editable = ('status',)
    
    def get_row_css(self, obj, index):
        if obj.priority == 'high':
            return 'red-row'
        return ''

# Скрываем стандартные группы, чтобы не мешали
admin.site.unregister(DjangoGroup)