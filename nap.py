import json
import logging
from datetime import datetime, timedelta
import os
TOKEN = os.getenv("TOKEN")
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

REMINDERS_FILE = "reminders.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------- utils ----------

def load_reminders():
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_reminders(data):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет 👋\n"
        "Напиши текст напоминания.\n"
        "Команда: /remind"
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши текст напоминания ✍️")
    context.user_data["waiting_text"] = True

# ---------- text ----------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_text"):
        context.user_data["reminder_text"] = update.message.text
        context.user_data["waiting_text"] = False

        keyboard = [
            [InlineKeyboardButton("Через дни (1–6)", callback_data="days_input")],
            [InlineKeyboardButton("Через недели (1–3)", callback_data="weeks_input")],
            [InlineKeyboardButton("Через месяцы (1–11)", callback_data="month_input")],
            [InlineKeyboardButton("Через год", callback_data="year")],
        ]

        await update.message.reply_text(
            "Когда напомнить?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

# ---------- buttons ----------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    now = datetime.now()

    if query.data == "days_input":
        context.user_data["waiting_days"] = True
        await query.edit_message_text("Введите количество дней (1–6):")
        return

    if query.data == "weeks_input":
        context.user_data["waiting_weeks"] = True
        await query.edit_message_text("Введите количество недель (1–3):")
        return

    if query.data == "month_input":
        context.user_data["waiting_month"] = True
        await query.edit_message_text("Введите количество месяцев (1–11):")
        return

    if query.data == "year":
        remind_time = now + timedelta(days=365)
        save_reminder(query.message.chat_id, context, remind_time)
        await query.edit_message_text(
            f"Готово ✅\nДата: {remind_time.strftime('%d.%m.%Y %H:%M')}"
        )

# ---------- inputs ----------

async def handle_days_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_days"):
        return

    try:
        days = int(update.message.text)
        if not 1 <= days <= 6:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите число от 1 до 6 ❗")
        return

    context.user_data["waiting_days"] = False
    remind_time = datetime.now() + timedelta(days=days)
    save_reminder(update.message.chat_id, context, remind_time)

    await update.message.reply_text(
        f"Готово ✅\nЧерез {days} дн.\n"
        f"Дата: {remind_time.strftime('%d.%m.%Y %H:%M')}"
    )

async def handle_weeks_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_weeks"):
        return

    try:
        weeks = int(update.message.text)
        if not 1 <= weeks <= 3:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите число от 1 до 3 ❗")
        returncontext.user_data["waiting_weeks"] = False
    remind_time = datetime.now() + timedelta(weeks=weeks)
    save_reminder(update.message.chat_id, context, remind_time)

    await update.message.reply_text(
        f"Готово ✅\nЧерез {weeks} нед.\n"
        f"Дата: {remind_time.strftime('%d.%m.%Y %H:%M')}"
    )

async def handle_month_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_month"):
        return

    try:
        months = int(update.message.text)
        if not 1 <= months <= 11:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите число от 1 до 11 ❗")
        return

    context.user_data["waiting_month"] = False
    remind_time = datetime.now() + timedelta(days=30 * months)
    save_reminder(update.message.chat_id, context, remind_time)

    await update.message.reply_text(
        f"Готово ✅\nЧерез {months} мес.\n"
        f"Дата: {remind_time.strftime('%d.%m.%Y %H:%M')}"
    )

# ---------- save ----------

def save_reminder(chat_id, context, remind_time):
    reminders = load_reminders()
    reminders.append({
        "chat_id": chat_id,
        "text": context.user_data["reminder_text"],
        "time": remind_time.isoformat(),
    })
    save_reminders(reminders)

# ---------- checker ----------

async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    reminders = load_reminders()
    now = datetime.now()
    remaining = []

    for r in reminders:
        if now >= datetime.fromisoformat(r["time"]):
            await context.bot.send_message(
                chat_id=r["chat_id"],
                text=f"⏰ Напоминание:\n{r['text']}",
            )
        else:
            remaining.append(r)

    save_reminders(remaining)

# ---------- main ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_days_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weeks_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_month_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.job_queue.run_repeating(check_reminders, interval=30, first=10)

    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":

    main()
