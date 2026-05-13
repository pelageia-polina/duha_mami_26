import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import time
import json
import os
import threading

# ========== НАСТРОЙКИ ==========
TOKEN = '8606403504:AAF-8haD7VYVz7xSS9HJ8kc6b-tGJxCeMjw'
ADMIN_CHAT_ID = 253546693  # Твой Telegram ID (узнать у @userinfobot)
QUEST_DURATION = 1800  # 30 минут в секундах

# Хранилище данных команд
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
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(KeyboardButton("📊 Статус фото"))
    markup.add(KeyboardButton("ℹ️ Осталось времени"))
    return markup

def get_completed_photos(user_id):
    """Возвращает список номеров уже сданных фото"""
    if user_id not in user_data:
        return []
    return user_data[user_id].get("completed_photos", [])

def count_completed(user_id):
    """Сколько фото уже сдано"""
    return len(get_completed_photos(user_id))

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
        time.sleep(QUEST_DURATION - 180)  # 27 минут
        if is_quest_active(user_id):
            bot.send_message(user_id, "⚠️ **ВНИМАНИЕ!** ⚠️\nДо конца квеста осталось **3 минуты**!\n\nУспейте отправить все фото!", parse_mode="Markdown")
    threading.Thread(target=warn, daemon=True).start()

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.chat.id)
    
    # Если команда уже зарегистрирована
    if user_id in user_data and "team_name" in user_data[user_id]:
        team_name = user_data[user_id]["team_name"]
        completed = count_completed(user_id)
        bot.send_message(message.chat.id, 
                        f"✅ Ты уже в команде **{team_name}**!\n\n"
                        f"📸 Отправляй фото с подписью: **номер задания** (1, 2, 3...)\n"
                        f"📊 Сдано фото: {completed}/10\n"
                        f"⏱ Осталось времени: {format_time_left(time_left(user_id))}",
                        parse_mode="Markdown", reply_markup=main_keyboard())
        return
    
    # Запрашиваем название команды
    msg = bot.send_message(message.chat.id, 
                          "🏆 **Добро пожаловать на квест!**\n\n"
                          "Придумайте название команды и отправьте его одним сообщением.\n\n"
                          "❗ Название должно быть уникальным (только буквы, цифры, пробелы).",
                          parse_mode="Markdown")
    bot.register_next_step_handler(msg, register_team)

def register_team(message):
    user_id = str(message.chat.id)
    team_name = message.text.strip()[:30]
    
    # Проверка на пустое название
    if not team_name or len(team_name) < 2:
        bot.send_message(message.chat.id, "❌ Название слишком короткое (минимум 2 символа). Попробуй еще раз через /start")
        return
    
    # Проверка, что такое название ещё не занято
    for uid, data in user_data.items():
        if data.get("team_name") == team_name:
            bot.send_message(message.chat.id, f"❌ Команда с названием **{team_name}** уже существует. Придумайте другое название и напишите /start", parse_mode="Markdown")
            return
    
    # Регистрируем команду
    user_data[user_id] = {
        "team_name": team_name,
        "completed_photos": [],  # номера сданных фото (1-10)
        "photos": {},  # словарь {номер: file_id}
        "start_time": None,
        "photo_times": {}
    }
    save_data()
    
    bot.send_message(message.chat.id,
                    f"✅ Команда **{team_name}** зарегистрирована!\n\n"
                    f"📸 **Как играть:**\n"
                    f"1. Выполните задание под номером 1\n"
                    f"2. Сделайте фото\n"
                    f"3. Отправьте фото в этот чат **с подписью**: `1`\n\n"
                    f"🕐 На квест даётся **30 минут**.\n"
                    f"📊 Статус фото можно проверить кнопкой ниже.\n\n"
                    f"🚀 Вперёд!",
                    parse_mode="Markdown", reply_markup=main_keyboard())
    
    # Уведомляем админа
    bot.send_message(ADMIN_CHAT_ID, f"✅ Зарегистрирована новая команда: **{team_name}**")

# ========== ПРИЁМ ФОТО С НОМЕРОМ ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = str(message.chat.id)
    
    # Проверка регистрации
    if user_id not in user_data or "team_name" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    
    team_name = user_data[user_id]["team_name"]
    
    # Проверка, есть ли номер задания (подпись к фото)
    caption = message.caption
    if not caption or not caption.strip().isdigit():
        bot.send_message(message.chat.id, 
                        "❌ **Неверный формат!**\n\n"
                        "Отправляя фото, обязательно укажи номер задания в подписи.\n\n"
                        "**Пример:** отправляешь фото для задания №5 → в поле «подпись» напиши `5`\n\n"
                        "Используй кнопку «📊 Статус фото», чтобы увидеть, какие номера ещё не сданы.",
                        parse_mode="Markdown")
        return
    
    photo_num = int(caption.strip())
    
    # Проверка, что номер в диапазоне 1-10
    if photo_num < 1 or photo_num > 10:
        bot.send_message(message.chat.id, "❌ Номер задания должен быть от 1 до 10. Попробуй ещё раз.")
        return
    
    # Запуск таймера при первом фото
    if user_data[user_id]["start_time"] is None:
        user_data[user_id]["start_time"] = time.time()
        save_data()
        bot.send_message(message.chat.id, 
                        "⏰ **КВЕСТ НАЧАЛСЯ!**\n"
                        f"У вас 30 минут. Время пошло!\n\n"
                        f"📸 Отправляйте фото с номерами 1-10.\n"
                        f"⏱ Время закончится через 30 минут.",
                        parse_mode="Markdown")
        bot.send_message(ADMIN_CHAT_ID, f"🚀 Команда **{team_name}** начала квест!")
        start_warning_timer(user_id)
    
    # Проверка, не истекло ли время
    if not is_quest_active(user_id):
        bot.send_message(message.chat.id, 
                        f"⏰ **Время вышло!** Квест окончен.\n\n"
                        f"📊 Сдано фото: {count_completed(user_id)}/10",
                        parse_mode="Markdown")
        return
    
    # Проверка, не сдано ли уже это фото
    if photo_num in user_data[user_id]["completed_photos"]:
        bot.send_message(message.chat.id, 
                        f"⚠️ Фото для задания №{photo_num} уже отправлено!\n\n"
                        f"📊 Осталось сдать номера: {get_missing_numbers(user_id)}",
                        parse_mode="Markdown")
        return
    
    # Сохраняем фото
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # Создаём папку для команды
    os.makedirs(f"quest_photos/{team_name}", exist_ok=True)
    
    timestamp = int(time.time())
    filename = f"quest_photos/{team_name}/{photo_num}_{timestamp}.jpg"
    with open(filename, 'wb') as f:
        f.write(downloaded_file)
    
    # Отмечаем фото как сданное
    user_data[user_id]["completed_photos"].append(photo_num)
    user_data[user_id]["photos"][photo_num] = file_id
    user_data[user_id]["photo_times"][photo_num] = timestamp
    save_data()
    
    completed = count_completed(user_id)
    missing = get_missing_numbers(user_id)
    
    response = f"✅ **Фото для задания №{photo_num} принято!**\n\n"
    response += f"📊 **Прогресс:** {completed}/10 фото сдано\n"
    
    if missing:
        response += f"📋 **Осталось сдать номера:** {', '.join(map(str, missing))}\n"
    
    response += f"⏱ **Осталось времени:** {format_time_left(time_left(user_id))}"
    
    if completed == 10:
        response += "\n\n🏆 **ПОЗДРАВЛЯЮ!** 🏆\nВы сдали ВСЕ 10 фото!\n\nЖдите окончания квеста для подведения итогов."
        bot.send_message(ADMIN_CHAT_ID, f"🎉 Команда **{team_name}** сдала ВСЕ 10 фото! Время: {format_time_left(time_left(user_id))} до конца")
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

def get_missing_numbers(user_id):
    """Возвращает список номеров, которые ещё не сданы"""
    completed = set(user_data[user_id]["completed_photos"])
    all_numbers = set(range(1, 11))
    missing = sorted(list(all_numbers - completed))
    return missing

# ========== КНОПКИ ==========
@bot.message_handler(func=lambda message: message.text == "📊 Статус фото")
def show_status(message):
    user_id = str(message.chat.id)
    
    if user_id not in user_data or "team_name" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    
    team_name = user_data[user_id]["team_name"]
    completed = count_completed(user_id)
    missing = get_missing_numbers(user_id)
    
    status_text = f"🏆 Команда: **{team_name}**\n\n"
    status_text += f"📸 **Сдано фото:** {completed}/10\n\n"
    
    # Показываем прогресс по каждому номеру
    status_text += "📋 **Детали:**\n"
    for i in range(1, 11):
        if i in user_data[user_id]["completed_photos"]:
            status_text += f"✅ Задание {i}\n"
        else:
            status_text += f"❌ Задание {i}\n"
    
    if missing:
        status_text += f"\n⏳ **Осталось сдать номера:** {', '.join(map(str, missing))}\n"
    
    if user_data[user_id]["start_time"]:
        if is_quest_active(user_id):
            status_text += f"\n⏱ **Осталось времени:** {format_time_left(time_left(user_id))}"
        else:
            status_text += f"\n⏰ **Квест окончен!**"
    
    bot.send_message(message.chat.id, status_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "ℹ️ Осталось времени")
def show_time(message):
    user_id = str(message.chat.id)
    
    if user_id not in user_data:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируй команду через /start")
        return
    
    if user_data[user_id]["start_time"] is None:
        bot.send_message(message.chat.id, "⏸ Квест ещё не начался. Отправь первое фото с номером задания!")
        return
    
    if is_quest_active(user_id):
        left = time_left(user_id)
        completed = count_completed(user_id)
        bot.send_message(message.chat.id, 
                        f"⏱ **Осталось времени:** {format_time_left(left)}\n\n"
                        f"📸 **Сдано фото:** {completed}/10\n"
                        f"📋 **Осталось номера:** {', '.join(map(str, get_missing_numbers(user_id)))}",
                        parse_mode="Markdown")
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
        completed = len(data["completed_photos"])
        start_time = data.get("start_time", 0)
        # Время завершения (если все 10) или текущее время
        finish_time = None
        if completed == 10:
            # Ищем время последнего фото
            if data["photo_times"]:
                finish_time = max(data["photo_times"].values())
        results.append({
            "team": data["team_name"],
            "completed": completed,
            "start_time": start_time,
            "finish_time": finish_time
        })
    
    # Сортировка: сначала те, у кого больше фото, потом по времени (кто раньше закончил)
    results.sort(key=lambda x: (-x["completed"], x["finish_time"] if x["finish_time"] else 9999999999))
    
    result_text = "🏆 **РЕЗУЛЬТАТЫ КВЕСТА** 🏆\n\n"
    for i, r in enumerate(results, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        time_str = ""
        if r["finish_time"] and r["completed"] == 10:
            # Время от старта до финиша
            duration = r["finish_time"] - r["start_time"]
            minutes = int(duration // 60)
            secs = int(duration % 60)
            time_str = f" (за {minutes} мин {secs} сек)"
        result_text += f"{medal} **{r['team']}** — {r['completed']}/10 фото{time_str}\n"
    
    bot.send_message(ADMIN_CHAT_ID, result_text, parse_mode="Markdown")

@bot.message_handler(commands=['stopquest'])
def admin_stop(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    for user_id in user_data:
        user_data[user_id]["start_time"] = 0
    save_data()
    bot.send_message(ADMIN_CHAT_ID, "⏹ Квест принудительно завершён для всех команд")

@bot.message_handler(commands=['teams'])
def admin_teams(message):
    """Список всех команд и их прогресс"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    if not user_data:
        bot.send_message(ADMIN_CHAT_ID, "Нет зарегистрированных команд")
        return
    
    text = "📋 **СПИСОК КОМАНД**\n\n"
    for user_id, data in user_data.items():
        completed = len(data["completed_photos"])
        status = "✅ активна" if data["start_time"] else "⏸ ожидает старта"
        text += f"• **{data['team_name']}** — {completed}/10 фото ({status})\n"
    
    bot.send_message(ADMIN_CHAT_ID, text, parse_mode="Markdown")

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
        print("⚠️ Не удалось отправить сообщение админу. Проверь ADMIN_CHAT_ID")
    bot.infinity_polling()