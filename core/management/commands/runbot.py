import telebot
from django.core.management.base import BaseCommand
from decouple import config
# Импортируем нашу новую модель ChatMessage
from core.models import Lead, LeadStatus, ChatMessage 

bot = telebot.TeleBot(config('TELEGRAM_BOT_TOKEN'))

class Command(BaseCommand):
    help = 'Запуск Telegram бота (Режим прослушки)'

    def handle(self, *args, **kwargs):
        print("🎧 Бот слушает сообщения...")
        bot.infinity_polling()

# Обработчик ВСЕХ текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Anon"
    first_name = message.from_user.first_name or "Client"
    text = message.text

    # 1. Ищем или создаем Лида
    lead, created = Lead.objects.get_or_create(
        telegram_id=user_id,
        defaults={
            'first_name': first_name,
            'telegram_username': username,
            'source': 'Telegram',
            'status': LeadStatus.NEW
        }
    )

    # 2. СОХРАНЯЕМ СООБЩЕНИЕ В БАЗУ (Вместо автоответа)
    ChatMessage.objects.create(
        lead=lead,
        text=text,
        is_from_manager=False # Это сообщение от клиента
    )

    print(f"📩 Сообщение от {first_name}: {text}")
    # Бот молчит, ничего не отправляет в ответ (bot.reply_to удален)