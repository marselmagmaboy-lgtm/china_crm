from django.contrib import admin
from django.urls import path, include
from core.views import chat_dashboard, index

urlpatterns = [
    # ГЛАВНАЯ СТРАНИЦА (Сайт)
    path('', index, name='index'),  # <--- Пустые кавычки = корень сайта

    # ЧАТ И АДМИНКА
    path('admin/chat/', chat_dashboard, name='chat_index'),
    path('admin/chat/<int:lead_id>/', chat_dashboard, name='chat_dashboard'),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
]