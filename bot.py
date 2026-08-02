import os
import sys
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus

# Токен бота
BOT_TOKEN = "8849435803:AAGCUhcFynX9EtPPMQyTILR0puMn2XgMeJI"

# Время неактивности (3 дня)
INACTIVE_DAYS = 3
INACTIVE_SECONDS = INACTIVE_DAYS * 24 * 60 * 60

# Создаём клиент
app = Client("kick_inactive_bot", bot_token=BOT_TOKEN)

# Хранилище времени последнего сообщения
last_message_time = {}

@app.on_message(filters.group & ~filters.service)
async def track_messages(client, message: Message):
    """Отслеживает активность пользователей"""
    if message.from_user:
        user_id = message.from_user.id
        last_message_time[user_id] = datetime.now()
        print(f"[{datetime.now()}] Обновлена активность: {message.from_user.first_name} (ID: {user_id})")

async def check_inactive_users():
    """Проверяет и кикает неактивных пользователей"""
    print("🔄 Запущена проверка неактивных пользователей")
    
    while True:
        await asyncio.sleep(60)  # Проверка каждую минуту (для теста)
        
        try:
            print(f"[{datetime.now()}] Начинаю проверку групп...")
            
            async for dialog in app.get_dialogs():
                if dialog.chat.type in ["group", "supergroup"]:
                    chat_id = dialog.chat.id
                    chat_title = dialog.chat.title
                    print(f"📊 Проверяю группу: {chat_title} (ID: {chat_id})")
                    
                    async for member in app.get_chat_members(chat_id):
                        user_id = member.user.id
                        
                        # Пропускаем ботов и админов
                        if member.user.is_bot:
                            continue
                        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                            continue
                        
                        last_seen = last_message_time.get(user_id)
                        
                        if last_seen:
                            time_diff = datetime.now() - last_seen
                            
                            if time_diff.total_seconds() > INACTIVE_SECONDS:
                                try:
                                    username = member.user.username or member.user.first_name
                                    print(f"🔨 Кикаю пользователя: {username} (ID: {user_id}) - не писал {time_diff.days} дней")
                                    
                                    # Кикаем
                                    await app.ban_chat_member(chat_id, user_id)
                                    await app.unban_chat_member(chat_id, user_id)
                                    
                                    # Уведомление
                                    mention = member.user.mention or member.user.first_name
                                    await app.send_message(
                                        chat_id,
                                        f"🔨 Пользователь {mention} не писал 3 дня. Кикаю его."
                                    )
                                    
                                    # Удаляем из словаря
                                    if user_id in last_message_time:
                                        del last_message_time[user_id]
                                    
                                except Exception as e:
                                    print(f"❌ Ошибка при кике {user_id}: {e}")
                        else:
                            # Если пользователь не писал с момента запуска бота
                            pass
                            
        except Exception as e:
            print(f"❌ Ошибка в проверке: {e}")

@app.on_message(filters.command("stats") & filters.group)
async def stats_command(client, message: Message):
    """Статистика активности"""
    if not message.from_user:
        return
    
    # Проверяем права (только админы могут смотреть статистику)
    member = await app.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        await message.reply("❌ Только администраторы могут использовать эту команду.")
        return
    
    total = 0
    active = 0
    inactive = 0
    
    async for member in app.get_chat_members(message.chat.id):
        if member.user.is_bot:
            continue
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            continue
            
        total += 1
        last_seen = last_message_time.get(member.user.id)
        
        if last_seen:
            time_diff = datetime.now() - last_seen
            if time_diff.total_seconds() > INACTIVE_SECONDS:
                inactive += 1
            else:
                active += 1
        else:
            inactive += 1
    
    await message.reply(
        f"📊 Статистика активности в группе:\n"
        f"👥 Всего пользователей: {total}\n"
        f"🟢 Активных: {active}\n"
        f"🔴 Неактивных (>3 дней): {inactive}"
    )

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    """Приветствие"""
    await message.reply(
        "👋 Привет! Я бот для кика неактивных пользователей.\n\n"
        "📌 Добавь меня в группу и дай права на удаление участников.\n"
        "⏰ Кикаю через 3 дня бездействия.\n\n"
        "🔧 Команды:\n"
        "/stats - статистика активности (только для админов)\n"
        "/ping - проверить работу бота"
    )

@app.on_message(filters.command("ping"))
async def ping_command(client, message: Message):
    """Проверка работы бота"""
    await message.reply("🏓 Pong! Бот работает.")

async def main():
    """Запуск бота"""
    print("🤖 Бот запущен!")
    print(f"📅 Время запуска: {datetime.now()}")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    
    await app.start()
    print("✅ Бот подключен к Telegram!")
    print("👤 Бот: @kick_for_tima_bot")
    
    # Запускаем проверку в фоне
    asyncio.create_task(check_inactive_users())
    
    # Держим бота активным
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Фикс для Python 3.14
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(main())
