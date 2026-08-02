import asyncio
from datetime import datetime, timedelta
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== КОНФИГ =====
BOT_TOKEN = "8849435803:AAGCUhcFynX9EtPPMQyTILR0puMn2XgMeJI"
OWNER_ID = 8131755675
INACTIVE_DAYS = 3

# ===== ХРАНИЛИЩА =====
last_msg = {}

# ===== ОСНОВНЫЕ ФУНКЦИИ =====

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отслеживает сообщения"""
    if update.message and update.message.from_user:
        user = update.message.from_user
        if not user.is_bot:
            last_msg[user.id] = datetime.now()

async def check_inactive(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет неактивных"""
    try:
        for chat_id in context.bot_data.get("groups", []):
            try:
                members = await context.bot.get_chat_administrators(chat_id)
                admin_ids = [m.user.id for m in members]
                
                async for member in context.bot.get_chat_members(chat_id):
                    if member.user.is_bot:
                        continue
                    if member.user.id in admin_ids:
                        continue
                    
                    last = last_msg.get(member.user.id)
                    if last:
                        if (datetime.now() - last).days >= INACTIVE_DAYS:
                            await context.bot.ban_chat_member(chat_id, member.user.id)
                            await context.bot.unban_chat_member(chat_id, member.user.id)
                            await context.bot.send_message(
                                chat_id,
                                f"🔨 {member.user.first_name} не писал {INACTIVE_DAYS} дня. Кикнут."
                            )
                            del last_msg[member.user.id]
            except:
                pass
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие"""
    if update.effective_user.id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("📋 Группы", callback_data="groups")],
            [InlineKeyboardButton("🔗 Ссылка", callback_data="link")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
        ]
        await update.message.reply_text(
            "🔐 **Панель управления**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("👋 Бот работает.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню"""
    if update.effective_user.id != OWNER_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Группы", callback_data="groups")],
        [InlineKeyboardButton("🔗 Ссылка", callback_data="link")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ]
    await update.message.reply_text(
        "🔐 **Панель управления**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("❌ Недостаточно прав")
        return
    
    data = query.data
    
    if data == "groups":
        await show_groups(query, context)
    elif data == "link":
        await get_link(query, context)
    elif data == "stats":
        await show_stats(query, context)
    elif data.startswith("group_"):
        chat_id = int(data.split("_")[1])
        await group_menu(query, context, chat_id)
    elif data.startswith("kick_"):
        chat_id = int(data.split("_")[1])
        await kick_menu(query, context, chat_id)
    elif data.startswith("kick_user_"):
        parts = data.split("_")
        chat_id = int(parts[1])
        user_id = int(parts[2])
        await kick_user(query, context, chat_id, user_id)
    elif data.startswith("name_"):
        chat_id = int(data.split("_")[1])
        await change_name(query, context, chat_id)
    elif data.startswith("photo_"):
        chat_id = int(data.split("_")[1])
        await change_photo(query, context, chat_id)
    elif data.startswith("promote_"):
        chat_id = int(data.split("_")[1])
        await promote_menu(query, context, chat_id)
    elif data.startswith("promote_user_"):
        parts = data.split("_")
        chat_id = int(parts[1])
        user_id = int(parts[2])
        await promote_user(query, context, chat_id, user_id)
    elif data == "back_menu":
        keyboard = [
            [InlineKeyboardButton("📋 Группы", callback_data="groups")],
            [InlineKeyboardButton("🔗 Ссылка", callback_data="link")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
        ]
        await query.edit_message_text(
            "🔐 **Панель управления**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ===== ГРУППЫ =====

async def show_groups(query, context):
    groups = []
    async for chat in context.bot.get_chat_members(query.message.chat.id):
        pass
    # Получаем все группы
    try:
        async for dialog in context.bot.get_chat(query.message.chat.id):
            pass
    except:
        pass
    
    # Простой способ - сохранять группы при добавлении бота
    groups = context.bot_data.get("groups", [])
    
    if not groups:
        await query.edit_message_text("❌ Нет групп")
        return
    
    keyboard = []
    for chat_id in groups[:10]:
        try:
            chat = await context.bot.get_chat(chat_id)
            title = chat.title[:20] + "..." if len(chat.title) > 20 else chat.title
            keyboard.append([InlineKeyboardButton(f"📁 {title}", callback_data=f"group_{chat_id}")])
        except:
            continue
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_menu")])
    await query.edit_message_text(
        f"📋 **Группы ({len(groups)})**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== МЕНЮ ГРУППЫ =====

async def group_menu(query, context, chat_id):
    try:
        chat = await context.bot.get_chat(chat_id)
        members_count = await context.bot.get_chat_member_count(chat_id)
        
        keyboard = [
            [InlineKeyboardButton("👥 Кик", callback_data=f"kick_{chat_id}")],
            [InlineKeyboardButton("✏️ Название", callback_data=f"name_{chat_id}")],
            [InlineKeyboardButton("🖼️ Фото", callback_data=f"photo_{chat_id}")],
            [InlineKeyboardButton("⭐ Права", callback_data=f"promote_{chat_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="groups")]
        ]
        
        await query.edit_message_text(
            f"📁 **{chat.title}**\n👥 {members_count} участников",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await query.edit_message_text("❌ Нет доступа")

# ===== КИК =====

async def kick_menu(query, context, chat_id):
    keyboard = []
    count = 0
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [a.user.id for a in admins]
        
        async for member in context.bot.get_chat_members(chat_id):
            if count >= 20:
                break
            if member.user.is_bot or member.user.id in admin_ids:
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
            await query.edit_message_text(
                "✅ Нет обычных пользователей",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]])
            )
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        await query.edit_message_text(
            "👥 **Кого кикнуть?**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await query.edit_message_text("❌ Ошибка")

async def kick_user(query, context, chat_id, user_id):
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await query.answer("✅ Кикнут!", show_alert=True)
        await group_menu(query, context, chat_id)
    except:
        await query.answer("❌ Ошибка", show_alert=True)

# ===== НАЗВАНИЕ =====

async def change_name(query, context, chat_id):
    await query.edit_message_text(
        "✏️ **Введи новое название**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]])
    )
    context.user_data["waiting_name"] = chat_id

# ===== ФОТО =====

async def change_photo(query, context, chat_id):
    await query.edit_message_text(
        "🖼️ **Отправь фото**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data=f"group_{chat_id}")]])
    )
    context.user_data["waiting_photo"] = chat_id

# ===== ПРАВА =====

async def promote_menu(query, context, chat_id):
    keyboard = []
    count = 0
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [a.user.id for a in admins]
        
        async for member in context.bot.get_chat_members(chat_id):
            if count >= 20:
                break
            if member.user.is_bot or member.user.id in admin_ids:
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
            await query.edit_message_text(
                "Нет пользователей",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]])
            )
            return
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")])
        await query.edit_message_text(
            "⭐ **Кому выдать права?**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await query.edit_message_text("❌ Ошибка")

async def promote_user(query, context, chat_id, user_id):
    try:
        await context.bot.promote_chat_member(
            chat_id, user_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        await query.answer("✅ Права выданы!", show_alert=True)
        await group_menu(query, context, chat_id)
    except:
        await query.answer("❌ Ошибка", show_alert=True)

# ===== ССЫЛКА =====

async def get_link(query, context):
    groups = context.bot_data.get("groups", [])
    
    if not groups:
        await query.edit_message_text("❌ Нет групп")
        return
    
    keyboard = []
    for chat_id in groups[:10]:
        try:
            chat = await context.bot.get_chat(chat_id)
            title = chat.title[:20] + "..."
            keyboard.append([InlineKeyboardButton(f"🔗 {title}", callback_data=f"genlink_{chat_id}")])
        except:
            continue
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_menu")])
    await query.edit_message_text(
        "🔗 **Выбери группу**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def generate_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        return
    
    chat_id = int(query.data.split("_")[1])
    try:
        link = await context.bot.create_chat_invite_link(chat_id, member_limit=1)
        await query.edit_message_text(
            f"🔗 **Ссылка:**\n`{link.invite_link}`\n\n⏳ 10 минут\n👤 1 пользователь",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"group_{chat_id}")]])
        )
    except:
        await query.edit_message_text("❌ Ошибка")

# ===== СТАТИСТИКА =====

async def show_stats(query, context):
    total_groups = 0
    total_users = 0
    inactive = 0
    
    groups = context.bot_data.get("groups", [])
    total_groups = len(groups)
    
    for chat_id in groups:
        try:
            async for member in context.bot.get_chat_members(chat_id):
                if not member.user.is_bot:
                    total_users += 1
                    last = last_msg.get(member.user.id)
                    if last and (datetime.now() - last).days >= INACTIVE_DAYS:
                        inactive += 1
        except:
            continue
    
    await query.edit_message_text(
        f"📊 **Статистика**\n\n📁 Групп: {total_groups}\n👥 Всего: {total_users}\n🔴 Неактивных: {inactive}\n🟢 Активных: {total_users - inactive}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_menu")]])
    )

# ===== ОБРАБОТЧИКИ СООБЩЕНИЙ =====

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста для смены названия"""
    if update.effective_user.id != OWNER_ID:
        return
    
    if "waiting_name" in context.user_data:
        chat_id = context.user_data.pop("waiting_name")
        try:
            await context.bot.set_chat_title(chat_id, update.message.text)
            await update.message.reply_text("✅ Название изменено")
        except:
            await update.message.reply_text("❌ Ошибка")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото для смены фото"""
    if update.effective_user.id != OWNER_ID:
        return
    
    if "waiting_photo" in context.user_data:
        chat_id = context.user_data.pop("waiting_photo")
        try:
            photo = await update.message.photo[-1].get_file()
            photo_path = f"photo_{chat_id}.jpg"
            await photo.download_to_drive(photo_path)
            await context.bot.set_chat_photo(chat_id, open(photo_path, "rb"))
            os.remove(photo_path)
            await update.message.reply_text("✅ Фото обновлено")
        except:
            await update.message.reply_text("❌ Ошибка")

# ===== ЗАПУСК =====

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Сохраняем группы при добавлении бота
    app.bot_data["groups"] = []
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("меню", menu))
    
    # Кнопки
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(generate_link, pattern=r"^genlink_"))
    
    # Сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.ALL, track))
    
    # Фоновая задача
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_inactive, interval=60, first=10)
    
    print("🤖 Бот запущен!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
