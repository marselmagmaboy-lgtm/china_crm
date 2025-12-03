from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import chat_dashboard, index, api_get_unread

urlpatterns = [
    path('', index, name='index'),
    path('admin/chat/', chat_dashboard, name='chat_index'),
    path('admin/chat/<int:lead_id>/', chat_dashboard, name='chat_dashboard'),
    path('api/unread-count/', api_get_unread, name='api_unread_count'),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
]

# ЭТО ВАЖНО: Разрешаем раздачу файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)