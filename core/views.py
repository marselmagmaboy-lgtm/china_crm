from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Max, Subquery, OuterRef
from .models import Lead, ChatMessage
import telebot
from decouple import config
import uuid

bot = telebot.TeleBot(config('TELEGRAM_BOT_TOKEN'))

def index(request):
    success = False
    if request.method == 'POST':
        name = request.POST.get('first_name')
        phone = request.POST.get('phone')
        if name and phone:
            fake_id = f"web_{uuid.uuid4().hex[:10]}"
            Lead.objects.create(first_name=name, phone=phone, source='Website', status='new', telegram_id=fake_id)
            success = True
    return render(request, 'index.html', {'success': success})

@staff_member_required
def api_get_unread(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        count = Lead.objects.filter(status='new').count()
        return JsonResponse({'count': count})
    return JsonResponse({'status': 'error'}, status=400)

@staff_member_required
def chat_dashboard(request, lead_id=None):
    # 1. Запрос для списка лидов (Сортировка)
    newest_msg = ChatMessage.objects.filter(lead=OuterRef('pk')).order_by('-created_at')
    
    leads = Lead.objects.annotate(
        last_msg_time=Max('messages__created_at'),
        last_msg_text=Subquery(newest_msg.values('text')[:1]),
        last_msg_type=Subquery(newest_msg.values('msg_type')[:1]) # Тип сообщения
    ).order_by('-status', '-last_msg_time', '-created_at')
    
    active_lead = None
    messages = []
    
    if lead_id:
        active_lead = get_object_or_404(Lead, id=lead_id)
        messages = active_lead.messages.all().order_by('created_at')
        
        # Если открыли чат - сбрасываем статус "Новый"
        if active_lead.status == 'new':
            active_lead.status = 'process'
            active_lead.save()

    # --- AJAX ОТВЕТ (ДЛЯ LIVE UPDATE) ---
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = {}
        
        # Данные для сайдбара (обновляем список слева)
        leads_data = []
        for l in leads:
            preview = l.last_msg_text
            if not preview:
                if l.last_msg_type == 'image': preview = '📷 Фото'
                elif l.last_msg_type == 'voice': preview = '🎤 Голосовое'
                else: preview = 'Нет сообщений'
            
            leads_data.append({
                'id': l.id,
                'name': l.first_name,
                'status': l.status,
                'time': l.last_msg_time.strftime("%H:%M") if l.last_msg_time else '',
                'preview': preview,
                'active': (l.id == active_lead.id) if active_lead else False
            })
        data['leads'] = leads_data

        # Данные сообщений (если открыт чат)
        if active_lead:
            msg_data = []
            for msg in messages:
                attachment_url = msg.attachment.url if msg.attachment else None
                msg_data.append({
                    'text': msg.text,
                    'is_manager': msg.is_from_manager,
                    'type': msg.msg_type,
                    'file_url': attachment_url,
                    'time': msg.created_at.strftime("%H:%M")
                })
            data['messages'] = msg_data
        
        return JsonResponse(data)

    # --- ОТПРАВКА СООБЩЕНИЯ ОТ АДМИНА ---
    if request.method == 'POST' and active_lead:
        text = request.POST.get('message_text')
        file = request.FILES.get('attachment') # Получаем файл
        
        try:
            # 1. Отправка в Телеграм
            tg_sent = False
            if active_lead.telegram_id and not active_lead.telegram_id.startswith('web_'):
                if file:
                    # Если есть файл
                    if file.content_type.startswith('image'):
                        bot.send_photo(active_lead.telegram_id, file, caption=text)
                        msg_type = 'image'
                    else:
                        bot.send_document(active_lead.telegram_id, file, caption=text)
                        msg_type = 'document'
                elif text:
                    bot.send_message(active_lead.telegram_id, text)
                    msg_type = 'text'
                tg_sent = True

            # 2. Сохранение в базу
            if tg_sent:
                ChatMessage.objects.create(
                    lead=active_lead, 
                    text=text, 
                    attachment=file,
                    msg_type=msg_type,
                    is_from_manager=True
                )
        except Exception as e:
            print(f"Ошибка отправки: {e}")
            
        return redirect('chat_dashboard', lead_id=lead_id)

    return render(request, 'admin/chat_dashboard.html', {
        'leads': leads,
        'active_lead': active_lead,
        'messages': messages,
    })