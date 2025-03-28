import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram import F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import docx
import mimetypes
import json
from aiogram.types import BotCommand

async def set_bot_commands():
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/info", description="Доступные команды бота"),
        BotCommand(command="/add_user", description="🙋🏻‍♂️ Добавить пользователя"),
        BotCommand(command="/remove_user", description="❌ Удалить пользователя из рассылки"),
        BotCommand(command="/list_users", description="📋 Список пользователей"),
        BotCommand(command="/alert_schedule_change", description="⚠️ Изменение в расписании"),
        BotCommand(command="/send_message", description="📢 Отправить сообщение конкретным пользователям"),
        BotCommand(command="/stats", description="📊 Статистика"),
        BotCommand(command="/clear_stats", description="❌ Сбросить статистику")
    ]
    await bot.set_my_commands(commands)

USER_FILE = "users.json"

STATS_FILE = "stats.json"

# Функция загрузки статистики из файла
def load_stats():
    default_stats = {
        "total_users": 0,
        "last_sent": 0,
        "read_messages": 0,
        "confirmed_read": 0,
        "reminders_sent": 0
    }
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as file:
            loaded_stats = json.load(file)
            # Обновляем словарь, если в файле нет каких-то ключей
            for key in default_stats:
                if key not in loaded_stats:
                    loaded_stats[key] = default_stats[key]
            return loaded_stats
    except (FileNotFoundError, json.JSONDecodeError):
        return default_stats


# Функция сохранения статистики в файл
def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as file:
        json.dump(stats, file, indent=4, ensure_ascii=False)

def load_stats():
    default_stats = {
        "total_users": 0,         # Всего пользователей
        "users_received": 0,      # Кто получил расписание
        "users_no_schedule": 0,   # Кому пришло "Записей нет"
        "read_messages": 0,       # Кто подтвердил чтение
        "reminders_sent": 0       # Отправлено напоминаний
    }

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as file:
            stats = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        stats = {}

    # Гарантируем, что в файле есть все нужные ключи
    for key in default_stats:
        if key not in stats:
            stats[key] = default_stats[key]

    with open(STATS_FILE, "w", encoding="utf-8") as file:
        json.dump(stats, file, indent=4, ensure_ascii=False)

    return stats


# Загружаем пользователей из файла
def load_users():
    try:
        with open("users.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print("⚠️ Файл users.json не найден, создаю новый...")
        return {}
    except json.JSONDecodeError:
        print("❌ Ошибка в файле users.json! Проверь JSON-структуру.")
        return {}

user_keywords = load_users()
print("🔹 Загруженные пользователи:", user_keywords)  # Отладка
stats_data = load_stats()
save_stats(stats_data)  # Сохраняем обновленные данные (если в файле чего-то не было)
print("🔹 Загруженные статистики:", stats_data)

def save_users():
    with open("users.json", "w", encoding="utf-8") as file:
        json.dump(user_keywords, file, indent=4, ensure_ascii=False)

API_TOKEN = '7707399273:AAGy66uY5HI2UipqZX1ogChK3L74Wgtl9cU'  # 🔹 Замените на ваш токен
ADMIN_ID = 440618281  # 🔹 Ваш Telegram ID (чтобы получать уведомления)

# 🔹 Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Бот с поддержкой HTML
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
router = Router()

# 🔹 Клавиатура с кнопкой "Отправить мой ID"
def get_id_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Отправить мой ID админу", callback_data="send_my_id")]
        ]
    )
    return keyboard

# 🔹 Текст с описанием функционала бота
BOT_DESCRIPTION = (
    "📺 <b>Добро пожаловать в бота телеканала «Беларусь 5»!</b>\n\n"
    "Этот бот автоматически отправляет вам <b>расписание трансляций</b>.\n"
    "Вы будете получать только те трансляции, которые <b>относятся к вам</b>.\n\n"
    "📩 <b>Как это работает?</b>\n"
    "1️⃣ Отправьте ваш ID админу, чтобы он добавил вас в рассылку.\n"
    "2️⃣ Когда выходит новое расписание, бот автоматически отправит вам ваш график.\n"
    "3️⃣ Вам не нужно писать боту — он все делает сам!\n\n"
    "⬇️ Нажмите кнопку ниже, чтобы отправить ваш ID админу."
)

# 🔹 Команда /info
@router.message(F.text == "/info")
async def send_info(message: types.Message):
        user_id = message.from_user.id

        # Общие команды для всех пользователей
        commands = [
            "/start - Запуск бота",
            "/info - Показать список команд",
        ]

        # Команды только для админа
        admin_commands = [
            "/add_user &lt;ID&gt; &lt;Ключевое слово&gt; - Добавить нового пользователя в рассылку",
            "/remove_user &lt;ID&gt; - Удалить пользователя из рассылки",
            "/list_users - Показать список пользователей в рассылке",
            "/alert_schedule_change - Предупредить об изменениях в расписании",
            "/send_message &lt;Ключевые слова&gt;, &lt;Сообщение&gt; - Отправить сообщение по ключевым словам",
        ]

        # Если это админ, добавляем админские команды
        if user_id == ADMIN_ID:
            commands += admin_commands

        # Формируем текст сообщения
        info_message = "<b>📌 Доступные команды:</b>\n\n" + "\n".join(commands)

        # Отправляем список команд пользователю
        await bot.send_message(user_id, info_message, parse_mode="HTML")

# 🔹 Команда /start
@router.message(F.text == "/start")
async def start_command(message: types.Message):
    await message.reply(BOT_DESCRIPTION, reply_markup=get_id_keyboard())

# 🔹 Команда /list_users (только для администратора)
@router.message(F.text == "/list_users")
async def list_users_command(message: types.Message):
    # Принудительно загружаем users.json перед отправкой списка
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            user_keywords = json.load(f)  # Перезаписываем переменную актуальными данными
    except FileNotFoundError:
        user_keywords = {}

    if not user_keywords:
        await message.reply("📋 Список пользователей пуст.")
        return

    users_text = "📋 Список пользователей:\n\n"
    for user_id, keyword in user_keywords.items():
        users_text += f"🆔 ID: {user_id} — 🔑 Ключевое слово: {keyword}\n"

    await message.reply(users_text)

import matplotlib.pyplot as plt
import io

@router.message(F.text.startswith("/stats"))
async def send_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return

    @router.message(F.text == "/clear_stats")
    async def clear_stats(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.reply("❌ У вас нет прав для выполнения этой команды.")
            return

        # Очищаем статистику
        stats_data.update({
            "total_users": len(user_keywords),  # Пользователи остаются
            "last_sent": 0,
            "read_messages": 0,
            "confirmed_read": 0,
            "reminders_sent": 0
        })

        save_stats(stats_data)  # Сохраняем изменения

        await message.reply("✅ Статистика успешно очищена!")
        logging.info("📊 Статистика сброшена администратором")

    # Обновляем количество пользователей
    stats_data["total_users"] = len(user_keywords)
    save_stats(stats_data)

    # Формируем текст отчета
    stats_text = (
        "<b>📊 Статистика бота:</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {stats_data['total_users']}\n"
        f"✅ <b>Получили расписание:</b> {stats_data['users_received']}\n"
        f"⚠️ <b>Нет записей в расписании:</b> {stats_data['users_no_schedule']}\n"
        f"👀 <b>Прочитали сообщение:</b> {stats_data.get('read_messages', 0)}\n"
        f"⏰ <b>Отправлено напоминаний:</b> {stats_data.get('reminders_sent', 0)}\n"
    )

    # Генерируем график и отправляем
    photo = generate_stats_chart(stats_data)
    await bot.send_photo(message.chat.id, photo, caption=stats_text)


# 🔹 Команда /alert_schedule_change (только для администратора)
@router.message(F.text == "/alert_schedule_change")
async def alert_schedule_change_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ У вас нет прав для выполнения этой команды.")
        return

    alert_text = "⚠️ <b>Внимание, изменение в расписании!</b>\nПросьба уточнить."
    sent_count = 0

    for user_id in user_keywords.keys():
        try:
            await bot.send_message(user_id, alert_text)
            sent_count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения пользователю {user_id}: {e}")

    await message.reply(f"✅ Уведомление отправлено {sent_count}/{len(user_keywords)} пользователям.")

# 🔹 Команда /add_user (только для администратора)
@router.message(F.text.startswith("/add_user"))
async def add_user_command(message: types.Message):
    try:
        _, user_id, keyword = message.text.split(maxsplit=2)

        # Принудительно загружаем актуальные данные
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                user_keywords = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            user_keywords = {}

        # Добавляем нового пользователя
        user_keywords[user_id] = keyword

        # Записываем изменения в файл
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(user_keywords, f, ensure_ascii=False, indent=4)

        await message.reply(f"✅ Пользователь {user_id} добавлен с ключевым словом '{keyword}'.")

    except ValueError:
        await message.reply("❌ Неверный формат. Используйте: /add_user [ID] [Ключевое слово]")

# 🔹 Команда /remove_user (только для администратора)
@router.message(F.text.startswith("/remove_user"))
async def remove_user_command(message: types.Message):
    try:
        _, user_id = message.text.split(maxsplit=1)

        # Принудительно загружаем актуальные данные
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                user_keywords = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            user_keywords = {}

        if user_id in user_keywords:
            del user_keywords[user_id]  # Удаляем из списка

            # Перезаписываем файл
            with open(USER_FILE, "w", encoding="utf-8") as f:
                json.dump(user_keywords, f, ensure_ascii=False, indent=4)

            await message.reply(f"✅ Пользователь {user_id} удален.")
        else:
            await message.reply("⚠️ Такого пользователя нет в списке.")

    except ValueError:
        await message.reply("❌ Неверный формат. Используйте: /remov_user [ID]")

@router.message(F.text.startswith("/send_message"))
async def send_custom_message(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⛔ У вас нет прав для использования этой команды.")
        return

    # Убираем команду и разбираем сообщение
    command_text = message.text[len("/send_message"):].strip()
    if not command_text:
        await message.reply("⚠️ Формат: `/send_message Ключевое слово, Другое слово, текст сообщения`")
        return

    # Отделяем ключевые слова от текста сообщения
    try:
        keywords_part, message_text = command_text.split(",", 1)
        keywords = [kw.strip().lower() for kw in keywords_part.split(",")]
    except ValueError:
        await message.reply("⚠️ Неверный формат. Используйте запятую между ключевыми словами и сообщением.")
        return

    sent_count = 0
    report_message = "<b>📢 Отчет по рассылке:</b>\n\n"

    for user_id, keyword in user_keywords.items():
        if keyword.lower() in keywords:  # Проверяем, есть ли ключевое слово в списке
            try:
                await bot.send_message(user_id, f"📢 {message_text}")
                sent_count += 1
                report_message += f"✅ <b>{user_id}</b> — {keyword}\n"
            except Exception as e:
                logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
                report_message += f"❌ <b>{user_id}</b> — {keyword} (Ошибка)\n"

    report_message += f"\n📨 <b>Всего отправлено сообщений:</b> {sent_count}/{len(keywords)}"

    # Отправляем админу отчет
    try:
        await bot.send_message(ADMIN_ID, report_message)
    except Exception as e:
        logger.error(f"❌ Ошибка отправки отчета админу: {e}")


# 🔹 Обработка нажатия на кнопку "Отправить мой ID"
@router.callback_query(F.data == "send_my_id")
async def send_user_id(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    username_text = f"@{username}" if username else "Нет username"

    message_to_admin = (
        "📩 <b>Новый пользователь отправил свой ID:</b>\n\n"
        f"🆔 <b>ID:</b> {user_id}\n"
        f"👤 <b>Имя пользователя:</b> {username_text}"
    )

    try:
        await bot.send_message(ADMIN_ID, message_to_admin)
        await callback.message.answer("✅ Ваш ID успешно отправлен админу! Ожидайте добавления в рассылку.")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ID админу: {e}")
        await callback.message.answer("⚠️ Ошибка при отправке ID админу.")

    await callback.answer()  # Закрывает "часики" на кнопке


# 🔹 Словарь для хранения загруженных файлов (чтобы потом обработать их по кнопке)
pending_files = {}

# 🔹 Клавиатура для подтверждения рассылки
def get_confirmation_keyboard(file_name):
    file_id = str(abs(hash(file_name)))  # Создаём уникальный идентификатор
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить рассылку", callback_data=f"confirm_send:{file_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_send:{file_id}")]
        ]
    )
    return keyboard

# 🔹 Функция поиска строк с ключевым словом
def extract_matching_rows(file_path, keyword):
    logger.info(f"🔍 Ищем слово '{keyword}' в файле {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type != 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        raise ValueError(f"Файл {file_path} не является документом Word.")

    doc = docx.Document(file_path)
    matching_rows = []

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if keyword.lower() in cell.text.lower():
                    matching_rows.append(row.cells)
                    break

    return matching_rows

# 🔹 Функция рассылки расписания и отчета админу
async def send_schedule_to_users(file_name, admin_id):
    sent_count = 0
    report_message = "<b>📢 Статус рассылки расписания:</b>\n\n"

    users_received_schedule = []  # Список пользователей с расписанием
    users_no_schedule = []  # Список пользователей без записей
    stats_data["users_received"] = 0
    stats_data["users_no_schedule"] = 0

    for user_id, keyword in user_keywords.items():
        matching_rows = extract_matching_rows(file_name, keyword)

        if not matching_rows:
            message_text = "⚠️ <b>Для вас нет записей в текущем расписании.</b>"
            users_no_schedule.append(f"{user_id} — {keyword}")  # Добавляем в список
            stats_data["users_no_schedule"] += 1
        else:
            message_text = "<b>📋 Ваше расписание:</b>\n\n"

            for row in matching_rows:
                try:
                    date = row[0].text.strip()
                    time = row[1].text.strip()
                    chron = row[2].text.strip()
                    fourth_column = row[3].text.strip()
                    creative_team = row[4].text.strip()
                    note = row[5].text.strip()

                    message_text += (
                        f"📅 <b>Дата:</b> {date}\n"
                        f"⏰ <b>Время:</b> {time}\n"
                        f"⏳ <b>Хрон:</b> {chron}\n"
                        f"📌 <b>4-й столбец:</b> {fourth_column}\n"
                        f"🎥 <b>Творческая бригада:</b> {creative_team}\n"
                        f"📝 <b>Примечание:</b> {note}\n"
                        "➖➖➖➖➖➖➖➖➖\n"
                    )
                except IndexError:
                    continue

            users_received_schedule.append(f"{user_id} — {keyword}")  # Добавляем в список
            stats_data["users_received"] += 1

        try:
            await bot.send_message(user_id, message_text)
            stats_data["last_sent"] += 1
            save_stats(stats_data)
            sent_count += 1
            stats_data["read_messages"] += 1
            save_stats(stats_data)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
            report_message += f"❌ <b>{user_id}</b> — {keyword} (Ошибка)\n"
    save_stats(stats_data)  # Сохраняем обновленные данные

    # 🔹 Добавляем в отчет список пользователей с расписанием и без
    if users_received_schedule:
        report_message += "\n✅ <b>Получили расписание:</b>\n" + "\n".join(users_received_schedule)

    if users_no_schedule:
        report_message += "\n⚠️ <b>Без записей в расписании:</b>\n" + "\n".join(users_no_schedule)

    report_message += f"\n📨 <b>Всего отправлено сообщений:</b> {sent_count}/{len(user_keywords)}"

    try:
        await bot.send_message(admin_id, report_message)
    except Exception as e:
        logger.error(f"❌ Ошибка отправки отчета админу: {e}")

# 🔹 Обработчик получения документа (с подтверждением рассылки)
@router.message(F.document)
async def handle_docs(message: types.Message):
    file_name = message.document.file_name
    file_id = str(abs(hash(file_name)))  # Генерируем ID для файла
    pending_files[file_id] = file_name   # Сохраняем файл с ID

    try:
        file_path = await bot.get_file(message.document.file_id)
        await bot.download_file(file_path.file_path, file_name)
        logger.info(f"📂 Файл {file_name} успешно загружен.")
    except Exception:
        await message.reply("⚠️ Ошибка при скачивании файла.")
        return

    # 🔹 Отправляем админу сообщение с выбором
    await bot.send_message(
        ADMIN_ID,
        f"📂 <b>Файл загружен:</b> {file_name}\n\nЧто вы хотите сделать?",
        reply_markup=get_confirmation_keyboard(file_name)
    )

# 🔹 Обработчик кнопки "Отправить рассылку"
@router.callback_query(F.data.startswith("confirm_send:"))
async def confirm_sending(callback: types.CallbackQuery):
    file_id = callback.data.split(":")[1]

    if file_id in pending_files:
        file_name = pending_files[file_id]
        await callback.message.edit_text(f"📢 <b>Начинаем рассылку...</b>")
        await send_schedule_to_users(file_name, ADMIN_ID)
        await callback.message.edit_text(f"✅ <b>Рассылка завершена!</b>")
        del pending_files[file_id]  # Удаляем из списка ожидания
    else:
        await callback.message.edit_text("⚠️ Файл не найден.")

    await callback.answer()

# 🔹 Обработчик кнопки "Отмена"
@router.callback_query(F.data.startswith("cancel_send:"))
async def cancel_sending(callback: types.CallbackQuery):
    file_id = callback.data.split(":")[1]

    if file_id in pending_files:
        await callback.message.edit_text(f"❌ <b>Рассылка отменена.</b>")
        del pending_files[file_id]  # Удаляем из списка ожидания
    else:
        await callback.message.edit_text("⚠️ Файл не найден.")

    await callback.answer()

def generate_stats_chart(data):
    labels = ["Получили\n расписание", "Нет записей", "Прочитали", "Напоминания"]
    values = [
        data["users_received"],
        data["users_no_schedule"],
        data["read_messages"],
        data["reminders_sent"]
    ]
    plt.figure(figsize=(6, 4))
    plt.bar(labels, values, color=["blue", "green", "red"])
    plt.title("Статистика бота")
    plt.xlabel("Параметры")
    plt.ylabel("Количество")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # Save to temp file
    plt.savefig('stats_chart.png')
    plt.close()

    # Return as InputFile
    return types.FSInputFile('stats_chart.png')


async def main():
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await bot.delete_webhook()
    await set_bot_commands()  # Устанавливаем команды
    await dispatcher.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
