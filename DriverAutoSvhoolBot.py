import telebot
import time
import secrets
import string
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ================== НАСТРОЙКИ ==================
TOKEN = "8524982503:AAEjMRxOCclieQANRwhpzAzujJOk1Gg4xdQ"
BOT_NAME = "DriverAutoSchool_bot"  # без @
CURATOR_ID = 761584410

ACCESS_TIME = 90 * 24 * 60 * 60  # 3 місяці

bot = telebot.TeleBot(TOKEN)

# ================== СХОВИЩА ==================
user_states = {}
user_access_time = {}
curator_reply_to = {}

# invite_code: user_id (None = ще не використаний)
invite_codes = {}

# ================== КЛАВІАТУРИ ==================
def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(
        KeyboardButton('Урок 1'), KeyboardButton('Урок 2'), KeyboardButton('Урок 3'),
        KeyboardButton('Урок 4'), KeyboardButton('Урок 5'), KeyboardButton('Урок 6'),
        KeyboardButton('Урок 7'), KeyboardButton('Урок 8'), KeyboardButton('Урок 9')
    )
    markup.add(
        KeyboardButton('Бонуси 🎁'),
        KeyboardButton('Книга 📕'),
        KeyboardButton('Куратор ➡️')
    )
    return markup

def get_curator_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Відповісти 📩", callback_data=f"reply_{user_id}")
    )
    return markup

# ================== ДОПОМІЖНЕ ==================
def is_access_valid(chat_id):
    start_time = user_access_time.get(chat_id)
    if not start_time:
        return False
    return time.time() - start_time <= ACCESS_TIME

def generate_invite_code():
    return ''.join(
        secrets.choice(string.ascii_letters + string.digits)
        for _ in range(12)
    )

# ================== /newlink ==================
@bot.message_handler(commands=['newlink'])
def new_link(message):
    if message.chat.id != CURATOR_ID:
        return

    code = generate_invite_code()
    invite_codes[code] = None

    link = f"https://t.me/{BOT_NAME}?start={code}"

    bot.reply_to(
        message,
        f"🔗 Одноразове посилання (3 місяці):\n{link}"
    )

# ================== /start ==================
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()

    if len(args) < 2:
        bot.reply_to(
            message,
            "⛔ Вхід тільки через спеціальне посилання 🔗"
        )
        return

    code = args[1]

    if code not in invite_codes:
        bot.reply_to(message, "⛔ Посилання недійсне")
        return

    if invite_codes[code] is not None:
        bot.reply_to(message, "⛔ Це посилання вже використане")
        return

    invite_codes[code] = message.chat.id
    user_access_time[message.chat.id] = time.time()
    user_states[message.chat.id] = None

    bot.reply_to(
        message,
        "✅ Доступ активовано на 3 місяці!\nОбери урок 👇",
        reply_markup=get_main_keyboard()
    )

# ================== ПОВІДОМЛЕННЯ ==================
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    text = message.text

    # перевірка доступу
    if chat_id != CURATOR_ID and not is_access_valid(chat_id):
        bot.reply_to(
            message,
            "⛔ Твій доступ завершився.\nОтримай нове посилання 🔗"
        )
        return

    # ===== КУРАТОР =====
    if text == 'Куратор ➡️':
        user_states[chat_id] = 'support'
        bot.reply_to(
            message,
            "💬 Напиши повідомлення куратору 👇",
            reply_markup=get_main_keyboard()
        )
        return

    if user_states.get(chat_id) == 'support' and chat_id != CURATOR_ID:
        username = f"@{message.from_user.username}" if message.from_user.username else "немає username"
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

        bot.send_message(
            CURATOR_ID,
            f"📩 Нове звернення\n👤 {full_name}\n{username}\n🆔 {chat_id}"
        )
        bot.forward_message(CURATOR_ID, chat_id, message.message_id)
        bot.send_message(
            CURATOR_ID,
            "Натисни для відповіді 👇",
            reply_markup=get_curator_keyboard(chat_id)
        )

        bot.reply_to(message, "✅ Повідомлення надіслано куратору")
        user_states[chat_id] = None
        return

    if chat_id == CURATOR_ID and curator_reply_to.get(chat_id):
        user_id = curator_reply_to.pop(chat_id)
        bot.send_message(
            user_id,
            f"💬 Відповідь від куратора:\n\n{text}"
        )
        bot.send_message(CURATOR_ID, "✅ Відповідь надіслано")
        return

    # ===== МЕНЮ =====
    if text and text.startswith('Урок '):
        bot.reply_to(message, f"{text} 🚀\nТут буде контент", reply_markup=get_main_keyboard())
    elif text == 'Бонуси 🎁':
        bot.reply_to(message, "🎁 Бонуси...", reply_markup=get_main_keyboard())
    elif text == 'Книга 📕':
        bot.reply_to(message, "📖 Книга...", reply_markup=get_main_keyboard())
    else:
        bot.reply_to(message, "Обери пункт меню 👇", reply_markup=get_main_keyboard())

# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def handle_reply(call):
    if call.message.chat.id != CURATOR_ID:
        return

    user_id = int(call.data.split('_')[1])
    curator_reply_to[CURATOR_ID] = user_id

    bot.answer_callback_query(call.id, "Режим відповіді")
    bot.send_message(
        CURATOR_ID,
        f"✍️ Напиши відповідь користувачу (ID: {user_id})"
    )

# ================== ЗАПУСК ==================
print("Бот запущений 🚀")
bot.infinity_polling()
