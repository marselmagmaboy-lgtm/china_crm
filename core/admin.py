from django.contrib import admin
from django.contrib.auth.models import Group as DjangoGroup
# Импортируем наши новые модели Lesson и Attendance
from .models import Lead, Student, Teacher, Group, Lesson, Attendance, Tariff, Payment, Task

# --- ВНУТРЕННИЕ ТАБЛИЦЫ (INLINES) ---
class AttendanceInline(admin.TabularInline):
    """Позволяет отмечать студентов внутри страницы Урока"""
    model = Attendance
    extra = 0
    autocomplete_fields = ['student']
    min_num = 1

# --- ОСНОВНЫЕ РАЗДЕЛЫ ---

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'phone', 'status', 'source', 'created_at')
    list_filter = ('status', 'source')
    search_fields = ('first_name', 'phone')
    list_editable = ('status',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'group', 'balance', 'student_status') # Добавили статус
    list_filter = ('group', 'student_status')
    search_fields = ('full_name', 'phone')

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
    inlines = [AttendanceInline] # Вставляем таблицу посещаемости внутрь

    def students_checked(self, obj):
        return obj.attendance_records.count()
    students_checked.short_description = "Отмечено чел."

# Убираем лишнее
admin.site.unregister(DjangoGroup)

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name', 'lessons_count', 'price')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'tariff', 'amount', 'date')
    list_filter = ('date', 'tariff')
    search_fields = ('student__full_name',)
    autocomplete_fields = ['student']
    
    # Запрещаем удалять и менять платежи, чтобы менеджеры не мухлевали
    # (Раскомментируй эти строки, когда сдашь проект в работу)
    # def has_delete_permission(self, request, obj=None):
    #     return False
    # def has_change_permission(self, request, obj=None):
    #     return False

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'deadline', 'priority', 'status')
    list_filter = ('status', 'priority', 'assigned_to')
    search_fields = ('title',)
    list_editable = ('status',) # Можно менять статус (Галочку) прямо в списке
    
    # Красим строки в зависимости от срочности (Фишка!)
    def get_row_css(self, obj, index):
        if obj.priority == 'high':
            return 'red-row'
        return ''    