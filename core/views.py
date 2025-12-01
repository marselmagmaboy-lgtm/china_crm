from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from .models import Lead, ChatMessage
import telebot
from decouple import config

# Инициализируем бота для отправки ответов
bot = telebot.TeleBot(config('TELEGRAM_BOT_TOKEN'))

@staff_member_required # Только для админов
def lead_chat(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Если менеджер отправил сообщение (нажал кнопку Отправить)
    if request.method == 'POST':
        # 1. Проверяем, что именно мы меняем
        if 'message_text' in request.POST:
            # ЭТО ОТПРАВКА СООБЩЕНИЯ
            text = request.POST.get('message_text')
            if text:
                # Отправляем в Реальный Телеграм
                try:
                    bot.send_message(lead.telegram_id, text)
                    # Сохраняем в историю
                    ChatMessage.objects.create(lead=lead, text=text, is_from_manager=True)
                except Exception as e:
                    print(f"Ошибка отправки: {e}")
        
        elif 'update_lead' in request.POST:
            # ЭТО ОБНОВЛЕНИЕ ДАННЫХ ЛИДА (Имя, цель и т.д.)
            lead.first_name = request.POST.get('first_name')
            lead.manager_comment = request.POST.get('manager_comment')
            lead.save()

        return redirect('lead_chat', lead_id=lead_id) # Перезагружаем страницу

    # Получаем все сообщения этого лида
    messages = lead.messages.all()
    
    return render(request, 'admin/lead_chat.html', {
        'lead': lead,
        'messages': messages
    })