import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import time
import json
import os
import threading

# ========== НАСТРОЙКИ ==========
TOKEN = '8606403504:AAF-8haD7VYVz7xSS9HJ8kc6b-tGJxCeMjw'
ADMIN_CHAT_ID = 253546693 # Твой Telegram ID (узнать через @userinfobot)
QUEST_DURATION = 1800  # 30 минут

# Задания с привязкой к случайным кодам
TASKS = {
    "G7hK3m": {"num": 1, "text": "Фото всей командой на скамейке: все одновременно подняли правую руку и левую ногу."},
    "Qw5RtY": {"num": 2, "text": "Фото, где каждый касается одного дерева разной частью тела."},
    "Xz9CvB": {"num": 3, "text": "Фото, где вся команда одновременно в прыжке, где все ноги оторваны от земли."},
    "Lp2NnM": {"num": 4, "text": "Фото, где одного человека держат все остальные любым способом."},
    "Fj7WsD": {"num": 5, "text": "Найдите лист древа и сфотографируйте его, держа его всеми участниками команды."},
    "Bv4HtE": {"num": 6, "text": "Фото, где все стоят по росту и руки лежат на плече у соседа."},
    "Rc9XyK": {"num": 7, "text": "Выложите лицо из любых подручных материалов. Сфотографируйте его."},
    "Tn2ZmQ": {"num": 8, "text": "Фото, где все показывают козу обеими руками."},
    "Wd6VpF": {"num": 9, "text": "Фото снизу. Встаньте в круг и обнимите друг друга за талию."},
    "Sy8LgH": {"num": 10, "text": "Фото с разными эмоциями (радость, грусть, злость, удивление, страх, спокойствие)."}
}

# Хранилище данных
user_data = {}
DATA_FILE = "quest_data.json"

bot = telebot.TeleBot(TOKEN)

# ========== ФУНКЦИИ ==========
def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

def main_keyboard():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(KeyboardButton("📊 Статус заданий"))
    markup.add(KeyboardButton("ℹ️ Осталось времени"))
    return markup

def count_completed_tasks(user_id):
    if user_id not in user_data:
        return 0
    return sum(1 for v in user_data[user_id]["completed"].values() if v)

def is_quest_active(user_id):
    if user_id not in user_data:
        return False
    if "start_time" not in user_data[user_id]:
        return False
    elapsed = time.time() - user_data[user_id]["start_time"]
    return elapsed < QUEST_DURATION

def time_left(user_id):
    if user_id not in user_data or "start_time" not in user_data[user_id]:
        return 0
    left = QUEST_DURATION - (time.time() - user_data[user_id]["start_time"])
    return max(0, int(left))

def format_time_left(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes} мин {secs} сек"

def start_warning_timer(user_id):
    """Предупреждение за 3 минуты до конца"""
    def warn():
        time.sleep(QUEST_DURATION - 180)
        if is_quest_active(user_id):
            bot.send_message(user_id, "⚠️ **ВНИМАНИЕ!** ⚠️\nДо конца квеста осталось **3 минуты**!\n\nУспейте отправить все фото!", parse_mode="Markdown")
    threading.Thread(target=warn, daemon=True).start()

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.chat.id)
    
    # Проверяем, есть ли параметр с кодом (пришёл из QR)
    try:
        payload = message.text.split(' ', 1)[1]  # /start G7hK3m
    except IndexError:
        payload = None
    
    # Если пользователь не зарегистрирован
    if user_id not in user_data or "team" not in user_data[user_id]:
        if payload and payload in TASKS:
            # Запоминаем, что это задание привязано к QR
            msg = bot.send_message(message.chat.id, "🏆 **Добро пожаловать на квест!**\n\nПридумайте название команды (одним сообщением):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, register_team, payload)
        else:
            msg = bot.send_message(message.chat.id, "🏆 **Добро пожаловать на квест!**\n\nПридумайте название команды (одним сообщением):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, register_team, None)
        return
    
    # Если уже зарегистрирован
    if payload and payload in TASKS:
        # Обрабатываем задание из QR
        process_task(user_id, payload, message.chat.id)
    else:
        bot.send_message(message.chat.id, f"Ты уже в команде **{user_data[user_id]['team']}**!\nИщи QR-коды на территории и сканируй их!", parse_mode="Markdown", reply_markup=main_keyboard())

def register_team(message, first_task_code=None):
    user_id = str(message.chat.id)
    team_name = message.text.strip()[:30]
    
    if not team_name or len(team_name) < 2:
        bot.send_message(message.chat.id, "❌ Название слишком короткое. Попробуй еще раз через /start")
        return
    
    # Создаём запись о команде
    user_data[user_id] = {
        "team": team_name,
        "completed": {code: False for code in TASKS.keys()},
        "start_time": None,
        "completed_history": []
    }
    save_data()
    
    bot.send_message(message.chat.id,
                    f"✅ Команда **{team_name}** зарегистрирована!\n\n"
                    f"🔍 Как играть:\n"
                    f"1. Найди QR-код на территории\n"
                    f"2. Наведи камеру → откроется задание\n"
                    f"3. Сделай фото\n"
                    f"4. Отправь фото **в этот чат**\n\n"
                    f"⏱ Время на квест: 30 минут\n"
                    f"🏆 Побеждает команда с максимальным количеством заданий!\n\n"
                    f"Первый QR найден? Вперёд! 🚀",
                    parse_mode="Markdown", reply_markup=main_keyboard())
    
    # Если регистрация была по QR-коду — сразу выдаём задание
    if first_task_code and first_task_code in TASKS:
        process_task(user_id, first_task_code, message.chat.id)

def process_task(user_id, code, chat_id):
    """Обрабатывает задание по коду из QR"""
    
    # Проверяем, существует ли задание с таким кодом
    if code not in TASKS:
        bot.send_message(chat_id, "❌ Неверный QR-код")
        return
    
    task = TASKS[code]
    task_num = task["num"]
    
    # Проверяем, выполнено ли уже это задание
    if user_data[user_id]["completed"].get(code, False):
        bot.send_message(chat_id, f"⚠️ Задание №{task_num} уже выполнено! Ищи другой QR-код.", parse_mode="Markdown")
        return
    
    # Если таймер не запущен — запускаем при первом задании
    if user_data[user_id]["start_time"] is None:
        user_data[user_id]["start_time"] = time.time()
        save_data()
        bot.send_message(chat_id, f"⏰ **КВЕСТ НАЧАЛСЯ!**\nУ вас 30 минут. Время пошло!\n\n📋 **Задание №{task_num}:** {task['text']}", parse_mode="Markdown")
        bot.send_message(ADMIN_CHAT_ID, f"🚀 Команда {user_data[user_id]['team']} начала квест!")
        start_warning_timer(user_id)
    else:
        if not is_quest_active(user_id):
            bot.send_message(chat_id, f"⏰ **Время вышло!** Квест окончен.\n\n✅ Выполнено заданий: {count_completed_tasks(user_id)} из {len(TASKS)}", parse_mode="Markdown")
            return
        bot.send_message(chat_id, f"📋 **Задание №{task_num}:** {task['text']}\n\n📸 Сделай фото и отправь его сюда!\n\n⏱ Осталось: {format_time_left(time_left(user_id))}", parse_mode="Markdown")
    
    # Запоминаем, какое задание сейчас выполняется
    user_data[user_id]["current_task"] = code
    save_data()

# ========== ПРИЁМ ФОТО ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = str(message.chat.id)
    
    if user_id not in user_data or "team" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    
    if not is_quest_active(user_id):
        bot.send_message(message.chat.id, f"⏰ **Время вышло!** Фото не принимаются.\n\n✅ Итог: выполнено {count_completed_tasks(user_id)} заданий", parse_mode="Markdown")
        return
    
    if "current_task" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❓ Сначала отсканируй QR-код с заданием!")
        return
    
    code = user_data[user_id]["current_task"]
    task = TASKS[code]
    task_num = task["num"]
    
    if user_data[user_id]["completed"].get(code, False):
        bot.send_message(message.chat.id, f"⚠️ Задание №{task_num} уже выполнено!")
        del user_data[user_id]["current_task"]
        save_data()
        return
    
    # Сохраняем фото
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    team_name = user_data[user_id]["team"]
    os.makedirs(f"quest_photos/{team_name}", exist_ok=True)
    
    timestamp = int(time.time())
    filename = f"quest_photos/{team_name}/{task_num}_{timestamp}.jpg"
    with open(filename, 'wb') as f:
        f.write(downloaded_file)
    
    # Отмечаем задание выполненным
    user_data[user_id]["completed"][code] = True
    user_data[user_id]["completed_history"].append({
        "task_num": task_num,
        "code": code,
        "time": timestamp,
        "photo": filename
    })
    
    completed = count_completed_tasks(user_id)
    total = len(TASKS)
    
    del user_data[user_id]["current_task"]
    save_data()
    
    response = f"✅ **Задание №{task_num} принято!**\n\n🎯 Выполнено: {completed}/{total}\n⏱ Осталось: {format_time_left(time_left(user_id))}"
    
    if completed == total:
        response += "\n\n🏆 **ПОЗДРАВЛЯЮ!** 🏆\nВы выполнили ВСЕ задания!"
        bot.send_message(ADMIN_CHAT_ID, f"🎉 Команда {team_name} выполнила ВСЕ 10 заданий!")
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

# ========== КНОПКИ ==========
@bot.message_handler(func=lambda message: message.text == "📊 Статус заданий")
def show_status(message):
    user_id = str(message.chat.id)
    
    if user_id not in user_data or "team" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    
    completed = count_completed_tasks(user_id)
    total = len(TASKS)
    
    status_text = f"🏆 Команда: **{user_data[user_id]['team']}**\n\n"
    status_text += f"✅ Выполнено: **{completed}/{total}**\n\n📋 Прогресс:\n"
    
    for code, task in TASKS.items():
        icon = "✅" if user_data[user_id]["completed"].get(code, False) else "❌"
        status_text += f"{icon} Задание {task['num']}\n"
    
    if user_data[user_id]["start_time"]:
        status_text += f"\n⏱ Осталось: {format_time_left(time_left(user_id))}"
    
    bot.send_message(message.chat.id, status_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "ℹ️ Осталось времени")
def show_time(message):
    user_id = str(message.chat.id)
    
    if user_id not in user_data:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    
    if user_data[user_id]["start_time"] is None:
        bot.send_message(message.chat.id, "⏸ Квест ещё не начался. Отсканируй первый QR-код!")
        return
    
    if is_quest_active(user_id):
        bot.send_message(message.chat.id, f"⏱ Осталось времени: **{format_time_left(time_left(user_id))}**\n\n✅ Выполнено: {count_completed_tasks(user_id)}/{len(TASKS)}", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⏰ **Квест окончен!** Время вышло.", parse_mode="Markdown")

# ========== АДМИН-КОМАНДЫ ==========
@bot.message_handler(commands=['results'])
def admin_results(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    if not user_data:
        bot.send_message(ADMIN_CHAT_ID, "Нет данных о командах")
        return
    
    results = []
    for user_id, data in user_data.items():
        completed = count_completed_tasks(user_id)
        results.append((data["team"], completed, data.get("start_time", 0)))
    
    results.sort(key=lambda x: (-x[1], x[2]))
    
    result_text = "🏆 **РЕЗУЛЬТАТЫ КВЕСТА** 🏆\n\n"
    for i, (team, completed, _) in enumerate(results, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        result_text += f"{medal} {team} — {completed}/10 заданий\n"
    
    bot.send_message(ADMIN_CHAT_ID, result_text, parse_mode="Markdown")

@bot.message_handler(commands=['stopquest'])
def admin_stop(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    for user_id in user_data:
        user_data[user_id]["start_time"] = 0
    save_data()
    bot.send_message(ADMIN_CHAT_ID, "⏹ Квест принудительно завершён для всех команд")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    load_data()
    os.makedirs("quest_photos", exist_ok=True)
    print("🤖 Бот запущен!")
    print(f"📸 Фото сохраняются в quest_photos/")
    print(f"👑 Админ: {ADMIN_CHAT_ID}")
    try:
        bot.send_message(ADMIN_CHAT_ID, "✅ Бот квеста запущен и готов к работе!")
    except:
        print("⚠️ Не удалось отправить сообщение админу")
    bot.infinity_polling()