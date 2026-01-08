import telebot
import time
import secrets
import string
import json
import os
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ================== НАСТРОЙКИ ==================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("⚠️ Не знайдено BOT_TOKEN! Задай змінну середовища: BOT_TOKEN=твій_токен")

BOT_NAME = "DriverAutoSchool_bot"  # без @
CURATOR_ID = 761584410  # твій Telegram ID

ACCESS_TIME = 90 * 24 * 60 * 60  # 90 днів = 3 місяці

bot = telebot.TeleBot(TOKEN)

# ================== ФАЙЛ ДАНИХ ==================
DATA_FILE = "bot_data.json"

# ================== СХОВИЩА ==================
user_states = {}          # стани користувачів (наприклад, підтримка)
user_access_time = {}     # час активації доступу
curator_reply_to = {}     # для відповіді куратора
invite_codes = {}         # код: user_id (None = не використано)

# ================== ЗАВАНТАЖЕННЯ ДАНИХ ==================
def load_data():
    global invite_codes, user_access_time
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                invite_codes = {k: v if v is not None else None for k, v in data.get("invite_codes", {}).items()}
                user_access_time = data.get("user_access_time", {})
                print("✅ Дані завантажено з файлу")
        except Exception as e:
            print(f"⚠️ Помилка завантаження даних: {e}")
    else:
        print("📄 Файл даних не знайдено — створено нові сховища")

def save_data():
    try:
        data = {
            "invite_codes": {k: v for k, v in invite_codes.items()},
            "user_access_time": user_access_time
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Помилка збереження даних: {e}")

load_data()

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
    if chat_id == CURATOR_ID:
        return True
    start_time = user_access_time.get(chat_id)
    if not start_time:
        return False
    return time.time() - start_time <= ACCESS_TIME

def generate_invite_code():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

# ================== КОМАНДИ ==================
@bot.message_handler(commands=['newlink'])
def new_link(message):
    if message.from_user.id != CURATOR_ID:
        bot.reply_to(message, "⛔ Доступ заборонено")
        return

    code = generate_invite_code()
    invite_codes[code] = None
    save_data()

    link = f"https://t.me/{BOT_NAME}?start={code}"

    bot.reply_to(
        message,
        f"🔗 Нове одноразове посилання (дійсне 3 місяці):\n\n{link}",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    args = message.text.split(maxsplit=1)

    # Куратор може просто написати /start і отримати меню
    if chat_id == CURATOR_ID:
        bot.send_message(
            chat_id,
            "👑 Ви увійшли як куратор!\n\nОбери дію 👇",
            reply_markup=get_main_keyboard()
        )
        return

    if len(args) < 2 or not args[1].strip():
        bot.send_message(
            chat_id,
            "👋 Вітаю в боті автошколи!\n\n⛔ Вхід можливий тільки за спеціальним одноразовим посиланням від куратора 🔗"
        )
        return

    code = args[1].strip()

    if code not in invite_codes:
        bot.reply_to(message, "⛔ Посилання недійсне або застаріле")
        return

    if invite_codes[code] is not None:
        bot.reply_to(message, "⛔ Це посилання вже було використано")
        return

    invite_codes[code] = chat_id
    user_access_time[chat_id] = time.time()
    user_states[chat_id] = None
    save_data()

    bot.send_message(
        chat_id,
        "✅ Доступ успішно активовано!\nТермін дії: 3 місяці з сьогодні\n\nОбери урок або розділ 👇",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(commands=['menu', 'help'])
def send_menu(message):
    chat_id = message.chat.id
    if chat_id == CURATOR_ID or is_access_valid(chat_id):
        bot.send_message(chat_id, "👇 Головне меню", reply_markup=get_main_keyboard())

# ================== ОБРОБКА ПОВІДОМЛЕНЬ ==================
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""

    # ===== КУРАТОР — ЗАВЖДИ МАЄ ДОСТУП І МЕНЮ =====
    if chat_id == CURATOR_ID:
        if text.startswith('Урок '):
            bot.reply_to(message, f"{text} 🚀\n\nТут буде матеріал уроку... (перегляд від куратора)", reply_markup=get_main_keyboard())
        elif text == 'Бонуси 🎁':
            bot.reply_to(message, "🎁 Бонуси та додаткові матеріали...\nСкоро тут з'явиться контент!", reply_markup=get_main_keyboard())
        elif text == 'Книга 📕':
            bot.reply_to(message, "📖 Посібник з ПДР та навчання...\nСкоро додамо!", reply_markup=get_main_keyboard())
        elif text == 'Куратор ➡️':
            bot.reply_to(message, "👑 Ти і є куратор! 😄\nМожеш писати повідомлення — вони прийдуть тобі ж для тестування.", reply_markup=get_main_keyboard())
        else:
            bot.reply_to(message, "👑 Кураторське меню 👇", reply_markup=get_main_keyboard())
        return

    # ===== ЗВИЧАЙНІ КОРИСТУВАЧІ — ПЕРЕВІРКА ДОСТУПУ =====
    if not is_access_valid(chat_id):
        bot.reply_to(
            message,
            "⛔ Твій доступ закінчився або не активований.\nЗвернись до куратора за новим посиланням 🔗"
        )
        return

    # ===== РЕЖИМ ПІДТРИМКИ =====
    if text == 'Куратор ➡️':
        user_states[chat_id] = 'support'
        bot.reply_to(
            message,
            "💬 Напиши своє питання чи повідомлення куратору 👇\n(Після надсилання ти повернешся в меню)",
            reply_markup=get_main_keyboard()
        )
        return

    if user_states.get(chat_id) == 'support':
        username = f"@{message.from_user.username}" if message.from_user.username else "(немає username)"
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Невідомо"

        info_text = f"📩 Нове звернення від учня:\n\n👤 {full_name}\n{username}\n🆔 ID: {chat_id}"

        bot.send_message(CURATOR_ID, info_text)
        bot.forward_message(CURATOR_ID, chat_id, message.message_id)
        bot.send_message(
            CURATOR_ID,
            "Натисни кнопку нижче, щоб відповісти 👇",
            reply_markup=get_curator_keyboard(chat_id)
        )

        bot.reply_to(message, "✅ Твоє повідомлення надіслано куратору!\nЧекай на відповідь 😊")
        user_states[chat_id] = None
        return

    # ===== ВІДПОВІДЬ ВІД КУРАТОРА =====
    if chat_id == CURATOR_ID and curator_reply_to.get(chat_id):
        user_id = curator_reply_to.pop(chat_id)
        bot.send_message(
            user_id,
            f"💬 Повідомлення від куратора:\n\n{message.text}"
        )
        bot.send_message(CURATOR_ID, "✅ Відповідь успішно надіслано учню", reply_markup=get_main_keyboard())
        return

    # ===== ГОЛОВНЕ МЕНЮ ДЛЯ КОРИСТУВАЧІВ =====
    if text.startswith('Урок '):
        bot.reply_to(message, f"{text} 🚀\n\nТут буде матеріал уроку...", reply_markup=get_main_keyboard())
    elif text == 'Бонуси 🎁':
        bot.reply_to(message, "🎁 Бонуси та додаткові матеріали...\nСкоро тут з'явиться контент!", reply_markup=get_main_keyboard())
    elif text == 'Книга 📕':
        bot.reply_to(message, "📖 Посібник з ПДР та навчання...\nСкоро додамо!", reply_markup=get_main_keyboard())
    else:
        bot.reply_to(message, "👇 Будь ласка, обери пункт з меню нижче", reply_markup=get_main_keyboard())

# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def handle_reply(call):
    if call.from_user.id != CURATOR_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ заборонено")
        return

    user_id = int(call.data.split('_')[1])
    curator_reply_to[CURATOR_ID] = user_id

    bot.answer_callback_query(call.id, "Режим відповіді активовано")
    bot.edit_message_text(
        chat_id=CURATOR_ID,
        message_id=call.message.message_id,
        text=f"✍️ Напиши відповідь користувачу (ID: {user_id}):"
    )

# ================== WEBHOOK З FLASK ==================
from flask import Flask, request, abort
import threading

app = Flask(__name__)

WEBHOOK_PATH = f"/{TOKEN}"

@app.route('/')
def index():
    return "Бот автошколи працює! 🚀"

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

def set_webhook():
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        full_url = webhook_url.rstrip("/") + WEBHOOK_PATH
        bot.remove_webhook()
        time.sleep(1)
        result = bot.set_webhook(url=full_url)
        if result:
            print(f"✅ Webhook успішно встановлено: {full_url}")
        else:
            print("❌ Не вдалося встановити webhook")
    else:
        print("⚠️ WEBHOOK_URL не задано — бот працюватиме в режимі polling (тільки для локального тестування)")

# ================== ЗАПУСК ==================
if __name__ == '__main__':
    threading.Thread(target=set_webhook).start()

    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Бот запущено на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    set_webhook()