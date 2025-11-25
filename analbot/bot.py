"""
bot.py
This module implements the Telegram bot for the analytics service. It
leverages the `pytelegrambotapi` library (imported as `telebot`) to handle
incoming messages and commands. The bot expects the following commands:

* `/start` – send a welcome message and brief instructions.
* `/help` – display help text describing available commands.
* `/upload` – instruct the user to send a CSV file containing sales data.
* `/report` – compute and return basic analytics over the uploaded data.
* `/forecast` – provide a naive forecast of future sales.

Incoming CSV files are parsed using pandas and stored in a SQLite
database via functions defined in the `data` module. The `analytics`
module contains the calculation logic for summarising and forecasting.
"""

import os
import io
import logging
from datetime import datetime, timedelta

import telebot
import pandas as pd

from .data import init_db, insert_sales
from .analytics import (
    calculate_daily_sales,
    calculate_average_check,
    get_top_products,
    forecast_sales,
)

# Configure basic logging. This will print messages to stdout when running
# the bot, which can be helpful for debugging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read configuration. The bot token should be provided via an environment
# variable for security. If not set, it falls back to a placeholder
# string, prompting developers to supply their own token.
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logger.warning(
        "Bot token not configured. Set the TELEGRAM_TOKEN environment variable"
    )

# Initialise database (creates tables if they do not exist).
init_db()

# Instantiate the bot.
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start", "help"])
def handle_start_help(message: telebot.types.Message) -> None:
    """Send a welcome/help message to the user."""
    help_text = (
        "Привет! Я бот аналитики для малого бизнеса. "
        "Я помогу тебе загрузить данные о продажах и получить аналитическую сводку.\n\n"
        "Доступные команды:\n"
        "/upload – загрузить CSV файл с продажами. "
        "Формат: дата, товар, количество, сумма.\n"
        "/report – получить отчёт по ключевым метрикам (выручка, средний чек, топ‑товары).\n"
        "/forecast – получить простой прогноз выручки на следующий день.\n"
        "Также можно прислать файл напрямую без команды – я автоматически его распознаю."
    )
    bot.reply_to(message, help_text)


@bot.message_handler(commands=["upload"])
def handle_upload_command(message: telebot.types.Message) -> None:
    """
    Instruct the user how to upload data. The actual file handling is
    performed in handle_document below. This command exists primarily for
    discoverability.
    """
    bot.reply_to(
        message,
        "Пожалуйста, отправьте CSV файл с вашими данными о продажах (дата, товар, количество, сумма).",
    )


@bot.message_handler(content_types=["document"])
def handle_document(message: telebot.types.Message) -> None:
    """
    Handle incoming files. The bot expects a CSV document, which it
    attempts to download, parse and insert into the database. If the
    document is not a CSV, a helpful error message is returned.
    """
    file_info = bot.get_file(message.document.file_id)
    file_name = message.document.file_name or "uploaded_file"

    # Only accept CSV files.
    if not file_name.lower().endswith(".csv"):
        bot.reply_to(
            message,
            "Пожалуйста, отправьте файл в формате CSV. Сейчас поддерживаются только CSV-файлы.",
        )
        return

    try:
        # Download file content
        downloaded_file = bot.download_file(file_info.file_path)
        # Wrap bytes into BytesIO for pandas
        data_stream = io.BytesIO(downloaded_file)
        df = pd.read_csv(data_stream)

        # Validate required columns
        expected_columns = {"date", "product", "quantity", "amount"}
        if not expected_columns.issubset({c.lower() for c in df.columns}):
            bot.reply_to(
                message,
                "Неверный формат файла. Ожидаются столбцы: date, product, quantity, amount.",
            )
            return

        # Normalise column names to lowercase
        df.columns = [c.lower() for c in df.columns]

        # Insert into DB
        rows_inserted = insert_sales(df)
        bot.reply_to(
            message,
            f"Файл успешно загружен и сохранён. Количество записей: {rows_inserted}.",
        )
    except Exception as exc:
        logger.exception("Error processing uploaded file", exc_info=exc)
        bot.reply_to(
            message,
            "Ошибка при обработке файла. Убедитесь, что файл корректен и повторите попытку.",
        )


@bot.message_handler(commands=["report"])
def handle_report(message: telebot.types.Message) -> None:
    """
    Generate a report with key metrics and send it to the user. The
    report includes daily revenue for the last seven days, the average
    check value and the top three products.
    """
    try:
        daily_sales = calculate_daily_sales(days=7)
        avg_check = calculate_average_check()
        top_products = get_top_products(limit=3)

        if not daily_sales:
            bot.reply_to(message, "В базе нет данных. Сначала загрузите файл с данными.")
            return

        # Format daily sales lines
        sales_lines = [
            f"{date}: {total:,.2f} ₽" for date, total in daily_sales
        ]
        sales_text = "\n".join(sales_lines)
        # Format top products
        top_lines = [
            f"{idx + 1}. {prod} — {total:,.2f} ₽" for idx, (prod, total) in enumerate(top_products)
        ]
        top_text = "\n".join(top_lines)

        report_text = (
            "*Ежедневная выручка (последние 7 дней):*\n"
            f"{sales_text}\n\n"
            f"*Средний чек:* {avg_check:,.2f} ₽\n\n"
            "*Топ‑3 товара:*\n"
            f"{top_text}"
        )
        bot.reply_to(message, report_text, parse_mode="Markdown")
    except Exception as exc:
        logger.exception("Error generating report", exc_info=exc)
        bot.reply_to(
            message,
            "Не удалось сформировать отчёт. Проверьте корректность данных и повторите попытку.",
        )


@bot.message_handler(commands=["forecast"])
def handle_forecast(message: telebot.types.Message) -> None:
    """
    Provide a simple forecast for the next day using naive averaging. It
    uses the last 7 days of sales to compute the expected value for
    tomorrow. If insufficient data is available, a message is returned.
    """
    try:
        forecast_value = forecast_sales(days=1)
        if forecast_value is None:
            bot.reply_to(
                message,
                "Недостаточно данных для прогноза. Нужно минимум 3 дня исторических данных.",
            )
            return

        tomorrow = datetime.now().date() + timedelta(days=1)
        bot.reply_to(
            message,
            f"Прогноз выручки на {tomorrow.strftime('%d.%m.%Y')}: {forecast_value:,.2f} ₽",
        )
    except Exception as exc:
        logger.exception("Error generating forecast", exc_info=exc)
        bot.reply_to(
            message,
            "Не удалось построить прогноз. Убедитесь, что данные корректны и попробуйте снова.",
        )


def main() -> None:
    """Entry point for launching the Telegram bot."""
    logger.info("Starting bot in polling mode...")
    # Polling ensures the script stays alive and continuously polls
    # Telegram for new messages. Use webhook for production if desired.
    bot.infinity_polling()


if __name__ == "__main__":
    main()