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
    raise ValueError("⚠️ Не знайдено BOT_TOKEN!")

BOT_NAME = "DriverAutoSchool_bot"
CURATOR_ID = 761584410
ACCESS_TIME = 90 * 24 * 60 * 60  # 90 днів

bot = telebot.TeleBot(TOKEN)

# ================== ДАНІ ==================
DATA_FILE = "bot_data.json"
user_states = {}          # 'support' або None
user_access_time = {}
curator_reply_to = {}
invite_codes = {}

def load_data():
    global invite_codes, user_access_time
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                invite_codes = {k: v if v is not None else None for k, v in data.get("invite_codes", {}).items()}
                user_access_time = data.get("user_access_time", {})
                print("✅ Дані завантажено")
        except Exception as e:
            print(f"⚠️ Помилка завантаження: {e}")

def save_data():
    try:
        data = {
            "invite_codes": {k: v for k, v in invite_codes.items()},
            "user_access_time": user_access_time
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Помилка збереження: {e}")

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
    markup.add(InlineKeyboardButton(f"Відповісти учню 📩 (ID: {user_id})", callback_data=f"reply_{user_id}"))
    return markup

# ================== ДОПОМІЖНЕ ==================
def is_access_valid(chat_id):
    if chat_id == CURATOR_ID:
        return True
    start_time = user_access_time.get(chat_id)
    return start_time and (time.time() - start_time <= ACCESS_TIME)

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
    bot.reply_to(message, f"🔗 Нове посилання:\n\n{link}")

@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split(maxsplit=1)
    chat_id = message.chat.id
    if len(args) < 2 or not args[1].strip():
        bot.send_message(chat_id, "👋 Вітаю!\n⛔ Вхід тільки за одноразовим посиланням від куратора.")
        return
    code = args[1].strip()
    if code not in invite_codes or invite_codes[code] is not None:
        bot.reply_to(message, "⛔ Посилання недійсне або вже використано")
        return
    invite_codes[code] = chat_id
    user_access_time[chat_id] = time.time()
    save_data()
    bot.send_message(chat_id, "✅ Доступ активовано на 3 місяці!\nОбери розділ 👇", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['menu', 'help'])
def send_menu(message):
    if is_access_valid(message.chat.id):
        bot.send_message(message.chat.id, "👇 Головне меню", reply_markup=get_main_keyboard())

# ================== ОБРОБКА ПОВІДОМЛЕНЬ ==================
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""

    if not is_access_valid(chat_id):
        bot.reply_to(message, "⛔ Твій доступ закінчився.\nЗвернись до куратора за новим посиланням 🔗")
        return

    # === Учень натискає "Куратор ➡️" — вмикаємо режим підтримки ===
    if text == 'Куратор ➡️':
        user_states[chat_id] = 'support'
        bot.reply_to(
            message,
            "💬 Тепер ти в режимі спілкування з куратором.\n"
            "Пиши повідомлення — вони будуть надіслані.\n\n"
            "Щоб вийти в меню — просто натисни будь-яку кнопку знизу (Урок, Бонуси тощо)",
            reply_markup=get_main_keyboard()
        )
        return

    # === Учень в режимі підтримки — надсилає повідомлення куратору (можна багато разів) ===
    if user_states.get(chat_id) == 'support' and chat_id != CURATOR_ID:
        # Перевіряємо, чи учень вийшов з режиму підтримки, натиснувши кнопку меню
        if text.startswith('Урок ') or text in ['Бонуси 🎁', 'Книга 📕', 'Куратор ➡️']:
            user_states[chat_id] = None  # виходимо з режиму
            # Далі обробка піде нижче як звичайне меню
        else:
            # Надсилаємо повідомлення куратору
            username = f"@{message.from_user.username}" if message.from_user.username else "(немає username)"
            full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip() or "Невідомо"

            info_text = f"📩 Повідомлення від учня:\n\n👤 {full_name}\n{username}\n🆔 ID: {chat_id}"

            bot.send_message(CURATOR_ID, info_text)
            bot.forward_message(CURATOR_ID, chat_id, message.message_id)
            bot.send_message(
                CURATOR_ID,
                "📝 Натисни кнопку, щоб відповісти 👇",
                reply_markup=get_curator_keyboard(chat_id)
            )

            bot.reply_to(message, "✅ Повідомлення надіслано куратору!\nПиши далі або вийди в меню кнопкою знизу.")
            return  # не виходимо з режиму — дозволяємо писати далі

    # === Куратор відповідає (режим активний) ===
    if chat_id == CURATOR_ID and curator_reply_to.get(CURATOR_ID) is not None:
        user_id = curator_reply_to[CURATOR_ID]

        if text.lower() in ['/stop', 'завершити', 'стоп', 'вихід']:
            del curator_reply_to[CURATOR_ID]
            bot.send_message(CURATOR_ID, "✅ Режим відповіді вимкнено.")
            return

        bot.send_message(user_id, f"💬 Повідомлення від куратора:\n\n{text}")
        bot.send_message(
            CURATOR_ID,
            "✅ Надіслано. Пиши далі або /stop для завершення.",
            reply_markup=get_curator_keyboard(user_id)
        )
        return

    # === Вихід з режиму підтримки — якщо учень натиснув кнопку меню ===
    if user_states.get(chat_id) == 'support' and (text.startswith('Урок ') or text in ['Бонуси 🎁', 'Книга 📕']):
        user_states[chat_id] = None  # явно виходимо

    # === Звичайна обробка меню ===
    if text.startswith('Урок '):
        bot.reply_to(message, f"{text} 🚀\n\nТут буде матеріал уроку...", reply_markup=get_main_keyboard())
    elif text == 'Бонуси 🎁':
        bot.reply_to(message, "🎁 Бонуси та додаткові матеріали...\nСкоро тут з'явиться контент!", reply_markup=get_main_keyboard())
    elif text == 'Книга 📕':
        bot.reply_to(message, "📖 Посібник з ПДР та навчання...\nСкоро додамо!", reply_markup=get_main_keyboard())
    else:
        bot.reply_to(message, "👇 Обери пункт з меню", reply_markup=get_main_keyboard())

# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def handle_reply(call):
    if call.from_user.id != CURATOR_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ заборонено")
        return

    user_id = int(call.data.split('_')[1])
    curator_reply_to[CURATOR_ID] = user_id

    bot.answer_callback_query(call.id, "✅ Активовано відповідь учню")

    bot.send_message(
        CURATOR_ID,
        f"✍️ <b>Ти пишеш учню (ID: {user_id})</b>\n\n"
        f"Надсилай повідомлення — вони підуть йому.\n"
        f"<i>Кнопка завжди активна. Завершити: /stop</i>",
        reply_markup=get_curator_keyboard(user_id),
        parse_mode="HTML"
    )

# ================== WEBHOOK ==================
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
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    abort(403)

def set_webhook():
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        url = webhook_url.rstrip("/") + WEBHOOK_PATH
        bot.remove_webhook()
        time.sleep(1)
        if bot.set_webhook(url=url):
            print(f"✅ Webhook: {url}")
        else:
            print("❌ Помилка webhook")
    else:
        print("⚠️ WEBHOOK_URL не задано — polling")

if __name__ == '__main__':
    threading.Thread(target=set_webhook).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
else:
    set_webhook()