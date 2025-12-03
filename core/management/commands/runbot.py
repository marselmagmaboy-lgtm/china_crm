import telebot
import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from decouple import config
from core.models import Lead, LeadStatus, ChatMessage

bot = telebot.TeleBot(config('TELEGRAM_BOT_TOKEN'))

class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **kwargs):
        print("🎧 Бот слушает (Текст, Фото, Голосовые)...")
        bot.infinity_polling()

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ПОИСКА ЛИДА ---
def get_or_create_lead(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Anon"
    first_name = message.from_user.first_name or "Client"
    
    lead, created = Lead.objects.get_or_create(
        telegram_id=user_id,
        defaults={
            'first_name': first_name,
            'telegram_username': username,
            'source': 'Telegram',
            'status': LeadStatus.NEW
        }
    )
    # Если лид был старый, обновляем статус, что он снова написал
    if not created and lead.status != 'new':
        lead.status = 'new' # Помечаем как непрочитанное
        lead.save()
        
    return lead

# --- 1. ОБРАБОТКА ТЕКСТА ---
@bot.message_handler(content_types=['text'])
def handle_text(message):
    lead = get_or_create_lead(message)
    ChatMessage.objects.create(lead=lead, text=message.text, msg_type='text')
    print(f"📩 Текст от {lead.first_name}")

# --- 2. ОБРАБОТКА ФОТО ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    lead = get_or_create_lead(message)
    
    # Берем самое большое фото из доступных размеров
    file_info = bot.get_file(message.photo[-1].file_id)
    file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
    
    # Скачиваем
    response = requests.get(file_url)
    
    if response.status_code == 200:
        msg = ChatMessage(lead=lead, text=message.caption or "", msg_type='image')
        # Сохраняем файл в Django
        file_name = f"photo_{message.message_id}.jpg"
        msg.attachment.save(file_name, ContentFile(response.content), save=True)
        print(f"📷 Фото от {lead.first_name}")

# --- 3. ОБРАБОТКА ГОЛОСОВЫХ ---
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    lead = get_or_create_lead(message)
    
    file_info = bot.get_file(message.voice.file_id)
    file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
    
    response = requests.get(file_url)
    
    if response.status_code == 200:
        msg = ChatMessage(lead=lead, msg_type='voice')
        file_name = f"voice_{message.message_id}.ogg"
        msg.attachment.save(file_name, ContentFile(response.content), save=True)
        print(f"🎤 Голосовое от {lead.first_name}")