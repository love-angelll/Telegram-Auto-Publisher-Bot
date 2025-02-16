import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

# Файлы данных
CONFIG_FILE = "config.json"
QUEUE_FILE = "queue.json"

# Загрузка конфигурации
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"TOKEN": "YOUR_BOT_TOKEN", "CHANNEL_ID": None, "INTERVAL": 300}

# Сохранение конфигурации
def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

# Загрузка очереди
def load_queue():
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Сохранение очереди
def save_queue():
    with open(QUEUE_FILE, "w", encoding="utf-8") as file:
        json.dump(queue, file, indent=4)

# Загружаем данные
config = load_config()
queue = load_queue()

TOKEN = config["TOKEN"]
CHANNEL_ID = config["CHANNEL_ID"]
interval = config["INTERVAL"]

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())

async def publish_messages():
    """Функция публикации сообщений с интервалом."""
    while True:
        if CHANNEL_ID and queue:
            message_data = queue.pop(0)
            save_queue()  # Сохраняем очередь после удаления сообщения
            try:
                await bot.copy_message(
                    chat_id=CHANNEL_ID,
                    from_chat_id=message_data["chat_id"],
                    message_id=message_data["message_id"]
                )
                logging.info(f"Опубликовано: {message_data['message_id']} в {CHANNEL_ID}")
            except Exception as e:
                logging.error(f"Ошибка публикации: {e}")
        await asyncio.sleep(interval)

@dp.message_handler(commands=['start'])
async def start(message: Message):
    await message.answer("Привет! Бот публикует сообщения с интервалом.\n"
                         "Используйте /set_channel @username или /set_channel -1001234567890 для настройки.")

@dp.message_handler(commands=['set_channel'])
async def set_channel(message: Message):
    """Установка канала для публикации."""
    global CHANNEL_ID
    try:
        new_channel = message.text.split()[1]
        if new_channel.startswith("@") or new_channel.lstrip("-").isdigit():
            CHANNEL_ID = new_channel
            config["CHANNEL_ID"] = CHANNEL_ID
            save_config(config)
            await message.answer(f"Канал установлен: {CHANNEL_ID}")
        else:
            await message.answer("Некорректный формат. Используйте /set_channel @username или ID.")
    except IndexError:
        await message.answer("Использование: /set_channel @username или /set_channel -1001234567890")

@dp.message_handler(commands=['set_interval'])
async def set_interval(message: Message):
    """Установка интервала публикации."""
    global interval
    try:
        new_interval = int(message.text.split()[1])
        interval = new_interval
        config["INTERVAL"] = interval
        save_config(config)
        await message.answer(f"Интервал установлен на {interval} секунд.")
    except (IndexError, ValueError):
        await message.answer("Использование: /set_interval <секунды>")

@dp.message_handler(commands=['stats'])
async def stats(message: Message):
    await message.answer(f"Очередь: {len(queue)} сообщений.")

@dp.message_handler(commands=['queue'])
async def show_queue(message: Message):
    """Просмотр очереди публикации."""
    if not queue:
        await message.answer("Очередь пуста.")
    else:
        text = '\n'.join([f"{i+1}: {msg['message_id']}" for i, msg in enumerate(queue)])
        await message.answer(f"Текущая очередь:\n{text}")

@dp.message_handler(commands=['remove'])
async def remove_from_queue(message: Message):
    """Удаление сообщения из очереди."""
    try:
        index = int(message.text.split()[1]) - 1
        if 0 <= index < len(queue):
            queue.pop(index)
            save_queue()
            await message.answer("Сообщение удалено.")
        else:
            await message.answer("Некорректный индекс.")
    except (IndexError, ValueError):
        await message.answer("Использование: /remove <номер>")

@dp.message_handler(commands=['clear_queue'])
async def clear_queue(message: Message):
    """Очистка всей очереди."""
    global queue
    queue = []
    save_queue()
    await message.answer("Очередь очищена.")

@dp.message_handler(commands=['publish_now'])
async def publish_now(message: Message):
    """Немедленная публикация сообщения из очереди."""
    if queue and CHANNEL_ID:
        msg_data = queue.pop(0)
        save_queue()
        try:
            await bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=msg_data["chat_id"],
                message_id=msg_data["message_id"]
            )
            await message.answer("Сообщение опубликовано.")
        except Exception as e:
            await message.answer(f"Ошибка публикации: {e}")
    else:
        await message.answer("Очередь пуста или канал не задан.")

@dp.message_handler(commands=['publish'])
async def publish(message: Message):
    """Немедленная публикация пересланного сообщения без добавления в очередь."""
    if message.reply_to_message and CHANNEL_ID:
        try:
            await bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id
            )
            await message.answer("Сообщение опубликовано.")
        except Exception as e:
            await message.answer(f"Ошибка публикации: {e}")
    else:
        await message.answer("Ответьте на сообщение, которое хотите опубликовать.")

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def add_to_queue(message: Message):
    """Добавление в очередь пересланного сообщения."""
    queue.append({"chat_id": message.chat.id, "message_id": message.message_id})
    save_queue()
    await message.answer("Сообщение добавлено в очередь.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(publish_messages())
    executor.start_polling(dp, skip_updates=True) 
