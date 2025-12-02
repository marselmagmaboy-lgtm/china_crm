from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Max
from .models import Lead, ChatMessage
import telebot
from decouple import config
from django.db.models import Subquery, OuterRef

bot = telebot.TeleBot(config('TELEGRAM_BOT_TOKEN'))

@staff_member_required
def chat_dashboard(request, lead_id=None):
    # --- ЛОГИКА ОПРЕДЕЛЕНИЯ "КТО ЖДЕТ ОТВЕТА" ---
    # Мы ищем лидов, у которых статус "Новый" ИЛИ последнее сообщение от клиента
    unanswered_count = Lead.objects.filter(
        status='new'
    ).count()

    # 1. AJAX-запрос (обновление каждые 2 сек)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = {'unanswered': unanswered_count} # Отправляем счетчик
        
        if lead_id:
            lead = get_object_or_404(Lead, id=lead_id)
            # Берем последние сообщения
            messages = lead.messages.all().order_by('created_at')
            msg_data = []
            for msg in messages:
                msg_data.append({
                    'text': msg.text,
                    'is_manager': msg.is_from_manager,
                    'time': msg.created_at.strftime("%H:%M")
                })
            data['messages'] = msg_data
            
        return JsonResponse(data)

    # 2. Обработка отправки (POST)
    if request.method == 'POST' and lead_id:
        lead = get_object_or_404(Lead, id=lead_id)
        text = request.POST.get('message_text')
        if text:
            try:
                bot.send_message(lead.telegram_id, text)
                ChatMessage.objects.create(lead=lead, text=text, is_from_manager=True)
                # Если ответили - меняем статус на "В обработке", чтобы счетчик уменьшился
                if lead.status == 'new':
                    lead.status = 'process'
                    lead.save()
            except Exception as e:
                print(f"Ошибка ТГ: {e}")
        return redirect('chat_dashboard', lead_id=lead_id)

    # 3. Обычная загрузка
    leads = Lead.objects.annotate(last_msg=Max('messages__created_at')).order_by('-last_msg', '-created_at')
    
    active_lead = None
    messages = []
    
    if lead_id:
        active_lead = get_object_or_404(Lead, id=lead_id)
        messages = active_lead.messages.all().order_by('created_at')

    return render(request, 'admin/chat_dashboard.html', {
        'leads': leads,
        'active_lead': active_lead,
        'messages': messages,
        'unanswered_count': unanswered_count, # Передаем начальное значение
    })

def index(request):
    success = False
    if request.method == 'POST':
        # Получаем данные из формы
        name = request.POST.get('first_name')
        phone = request.POST.get('phone')
        
        if name and phone:
            # Создаем Лида в базе
            Lead.objects.create(
                first_name=name,
                phone=phone,
                source='Website',     # Источник - Сайт
                status='new'          # Статус - Новый
            )
            success = True
            
    return render(request, 'index.html', {'success': success})