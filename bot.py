import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import time
import json
import os
from datetime import datetime
import threading

TOKEN = 'ВСТАВЬ_СВОЙ_ТОКЕН'
ADMIN_CHAT_ID = 123456789
QUEST_DURATION = 1800

TASKS = {
    "task1": "Фото всей командой на скамейке: все одновременно подняли правую руку и левую ногу.",
    "task2": "Фото, где каждый касается одного дерева разной частью тела.",
    "task3": "Фото, где вся команда одновременно в прыжке, где все ноги оторваны от земли.",
    "task4": "Фото, где одного человека держат все остальные любым способом.",
    "task5": "Найдите лист древа и сфотографируйте его, держа его всеми участниками команды.",
    "task6": "Фото, где все стоят по росту и руки лежат на плече у соседа.",
    "task7": "Выложите лицо из любых подручных материалов. Сфотографируйте его.",
    "task8": "Фото, где все показывают козу обеими руками.",
    "task9": "Фото снизу. Встаньте в круг и обнимите друг друга за талию.",
    "task10": "Фото с разными эмоциями (радость, грусть, злость, удивление, страх, спокойствие)."
}

user_data = {}
DATA_FILE = "quest_data.json"

def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

bot = telebot.TeleBot(TOKEN)

def main_keyboard():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(KeyboardButton("📊 Статус заданий"))
    markup.add(KeyboardButton("ℹ️ Осталось времени"))
    return markup

def get_user_task_status(user_id):
    if str(user_id) not in user_data:
        return {}
    return user_data[str(user_id)].get("tasks", {})

def count_completed_tasks(user_id):
    tasks = get_user_task_status(user_id)
    return sum(1 for v in tasks.values() if v)

def is_quest_active(user_id):
    if str(user_id) not in user_data:
        return False
    if "start_time" not in user_data[str(user_id)]:
        return False
    elapsed = time.time() - user_data[str(user_id)]["start_time"]
    return elapsed < QUEST_DURATION

def time_left(user_id):
    if str(user_id) not in user_data or "start_time" not in user_data[str(user_id)]:
        return 0
    elapsed = time.time() - user_data[str(user_id)]["start_time"]
    left = QUEST_DURATION - elapsed
    return max(0, int(left))

def format_time_left(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes} мин {secs} сек"

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.chat.id)
    if user_id in user_data and "team" in user_data[user_id]:
        bot.send_message(message.chat.id, f"Ты уже в команде {user_data[user_id]['team']}!\nИспользуй QR-коды для заданий.", reply_markup=main_keyboard())
        return
    msg = bot.send_message(message.chat.id, "🏆 Добро пожаловать на квест!\n\nПридумайте название команды и отправьте его одним сообщением.")
    bot.register_next_step_handler(msg, register_team)

def register_team(message):
    user_id = str(message.chat.id)
    team_name = message.text.strip()[:30]
    if not team_name or len(team_name) < 2:
        bot.send_message(message.chat.id, "❌ Название слишком короткое. Попробуй еще раз через /start")
        return
    user_data[user_id] = {
        "team": team_name,
        "tasks": {task_id: False for task_id in TASKS.keys()},
        "start_time": None,
        "completed_history": []
    }
    save_data()
    bot.send_message(message.chat.id, f"✅ Команда {team_name} зарегистрирована!\n\n🔍 Ищите QR-коды и сканируйте их!", reply_markup=main_keyboard())

@bot.message_handler(commands=['task1', 'task2', 'task3', 'task4', 'task5', 'task6', 'task7', 'task8', 'task9', 'task10'])
def get_task_by_qr(message):
    user_id = str(message.chat.id)
    task_id = message.text[1:]
    if user_id not in user_data or "team" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    if task_id not in TASKS:
        bot.send_message(message.chat.id, "❌ Неверное задание")
        return
    if user_data[user_id]["start_time"] is None:
        user_data[user_id]["start_time"] = time.time()
        save_data()
        bot.send_message(message.chat.id, f"⏰ КВЕСТ НАЧАЛСЯ! У вас 30 минут!\n\n📋 Задание: {TASKS[task_id]}")
        bot.send_message(ADMIN_CHAT_ID, f"🚀 Команда {user_data[user_id]['team']} начала квест!")
    else:
        if not is_quest_active(user_id):
            bot.send_message(message.chat.id, f"⏰ Время вышло! Выполнено: {count_completed_tasks(user_id)} из {len(TASKS)}")
            return
        if user_data[user_id]["tasks"].get(task_id, False):
            bot.send_message(message.chat.id, f"⚠️ Задание уже выполнено! Осталось времени: {format_time_left(time_left(user_id))}")
            return
        bot.send_message(message.chat.id, f"📋 Задание:\n{TASKS[task_id]}\n\n⏱ Осталось: {format_time_left(time_left(user_id))}")
    user_data[user_id]["current_task"] = task_id
    save_data()

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = str(message.chat.id)
    if user_id not in user_data or "team" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    if not is_quest_active(user_id):
        bot.send_message(message.chat.id, f"⏰ Время вышло! Итог: {count_completed_tasks(user_id)} заданий")
        return
    if "current_task" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❓ Сначала отсканируй QR-код с заданием!")
        return
    task_id = user_data[user_id]["current_task"]
    if user_data[user_id]["tasks"].get(task_id, False):
        bot.send_message(message.chat.id, "⚠️ Это задание уже выполнено!")
        del user_data[user_id]["current_task"]
        save_data()
        return
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    team_name = user_data[user_id]["team"]
    os.makedirs(f"quest_photos/{team_name}", exist_ok=True)
    timestamp = int(time.time())
    filename = f"quest_photos/{team_name}/{task_id}_{timestamp}.jpg"
    with open(filename, 'wb') as f:
        f.write(downloaded_file)
    user_data[user_id]["tasks"][task_id] = True
    user_data[user_id]["completed_history"].append({"task": task_id, "time": timestamp, "photo": filename})
    completed = count_completed_tasks(user_id)
    del user_data[user_id]["current_task"]
    save_data()
    response = f"✅ Задание принято!\n\n🎯 Выполнено: {completed}/{len(TASKS)}\n⏱ Осталось: {format_time_left(time_left(user_id))}"
    if completed == len(TASKS):
        response += "\n\n🏆 ПОЗДРАВЛЯЮ! Вы выполнили ВСЕ задания!"
        bot.send_message(ADMIN_CHAT_ID, f"🎉 Команда {team_name} выполнила ВСЕ задания!")
    bot.send_message(message.chat.id, response)

@bot.message_handler(func=lambda message: message.text == "📊 Статус заданий")
def show_status(message):
    user_id = str(message.chat.id)
    if user_id not in user_data or "team" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    tasks = get_user_task_status(user_id)
    completed = count_completed_tasks(user_id)
    status_text = f"🏆 Команда: {user_data[user_id]['team']}\n\n✅ Выполнено: {completed}/{len(TASKS)}\n\n"
    for i, task_key in enumerate(TASKS.keys(), 1):
        icon = "✅" if tasks.get(task_key, False) else "❌"
        status_text += f"{icon} Задание {i}\n"
    if user_data[user_id]["start_time"]:
        status_text += f"\n⏱ Осталось: {format_time_left(time_left(user_id))}"
    bot.send_message(message.chat.id, status_text)

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
        bot.send_message(message.chat.id, f"⏱ Осталось: {format_time_left(time_left(user_id))}\n\n✅ Выполнено: {count_completed_tasks(user_id)}/{len(TASKS)}")
    else:
        bot.send_message(message.chat.id, "⏰ Квест окончен!")

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
    result_text = "🏆 РЕЗУЛЬТАТЫ КВЕСТА 🏆\n\n"
    for i, (team, completed, _) in enumerate(results, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        result_text += f"{medal} {team} — {completed}/10 заданий\n"
    bot.send_message(ADMIN_CHAT_ID, result_text)

if __name__ == "__main__":
    load_data()
    os.makedirs("quest_photos", exist_ok=True)
    print("🤖 Бот запущен!")
    bot.infinity_polling()