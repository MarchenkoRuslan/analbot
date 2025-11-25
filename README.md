# Analbot – Telegram Bot for Small Business Analytics

Analbot is a simple Telegram bot that helps owners of small businesses
make sense of their sales data. The bot allows you to upload a CSV
file containing your transactions and then returns key metrics such as
daily revenue, average check value and the most popular products. It
also provides a naïve forecast of tomorrow’s revenue based on recent
history.

## Features

- **Data import:** Upload your sales data in CSV format directly in
  Telegram. The file must have the following columns (case
  insensitive): `date`, `product`, `quantity`, `amount`.
- **Daily revenue:** Get a summary of your revenue per day for the
  last seven days.
- **Average check:** Understand how much your customers typically
  spend per purchase.
- **Top products:** See which items contribute the most to your
  revenue.
- **Forecast:** Receive a simple forecast for tomorrow’s revenue
  computed as the average of the last seven days.

## Installation

1. **Clone the repository** (or download the source code):

   ```bash
   git clone https://github.com/MarchenkoRuslan/analbot.git
   cd analbot
   ```

2. **Install dependencies**. We recommend using a virtual environment.

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure the bot token.** Create a new bot via [@BotFather](https://t.me/botfather) in Telegram and copy the API token. Set
   this token in the environment before running the bot:

   ```bash
   export TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```

   Alternatively, you can hardcode the token in `bot.py` by replacing
   the placeholder string.

4. **Run the bot**:

   ```bash
   python -m analbot.bot
   ```

   The bot will start in polling mode and begin listening for
   messages. You should now be able to find your bot in Telegram by
   its username and start interacting with it.

## Usage

After launching the bot and starting a chat with it, use the
following commands:

- `/start` or `/help` – display a welcome message and list of
  commands.
- `/upload` – instructs you to send a CSV file. You can also just
  attach the file directly without sending the command first.
- `/report` – generates an analytics report containing daily revenue
  for the last seven days, the average check value and the top three
  products.
- `/forecast` – returns a naïve forecast of the next day’s revenue.

## CSV Format

The bot currently recognises CSV files with the following columns:

| Column   | Description                                          |
|---------:|------------------------------------------------------|
| `date`   | Date of the sale (any parseable format).             |
| `product`| Name or identifier of the product sold.             |
| `quantity` | Quantity of items sold (integer).                  |
| `amount` | Revenue from the sale (float).                      |

Column names are case‑insensitive. Dates are normalised to ISO
format (YYYY‑MM‑DD) internally. If your CSV contains additional
columns, they will be ignored. Each row should represent a single sale
transaction. The bot stores uploaded data locally in a SQLite
database under the `db/` directory.

## Notes

- The forecast provided by this MVP is deliberately simple: it
  computes the average of the last seven days’ total revenue. In a
  production environment you might replace this with a more
  sophisticated model (e.g. ARIMA, Prophet).
- Data is stored in a local SQLite database (`db/database.db`). You can
  back up or delete this file as needed. Multiple users are not
  currently separated in this MVP.
- For production use, consider deploying the bot on a VPS and
  configuring a Telegram webhook instead of polling for better
  efficiency.

## License

This project is released under the MIT License. See the
`LICENSE` file for details.