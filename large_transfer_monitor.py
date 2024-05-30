import os
import requests
import json
import logging
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("news_transfers.txt", mode='w'),  # Overwrite news_transfers.txt
    logging.StreamHandler()
])

# Set API keys and monitoring addresses
COINGECKO_API_URL = os.getenv('COINGECKO_API_URL')
if not COINGECKO_API_URL:
    raise ValueError("COINGECKO_API_URL is not set. Please check your environment variables.")

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OPENAI_API_SECRET_KEY = os.getenv('OPENAI_API_SECRET_KEY')
OPENAI_BASE_API_URL = os.getenv('OPENAI_BASE_API_URL')
ETH_THRESHOLD_STRING = os.getenv('ETH_THRESHOLD', '100')  # ETH large transaction threshold (in ETH)
BTC_THRESHOLD_STRING = os.getenv('BTC_THRESHOLD', '10')   # BTC large transaction threshold (in BTC)

# Convert threshold values to float
try:
    ETH_THRESHOLD = float(ETH_THRESHOLD_STRING)
except ValueError:
    logging.error(f"Invalid ETH_THRESHOLD value: {ETH_THRESHOLD_STRING}. Using default value 100.")
    ETH_THRESHOLD = 100.0

try:
    BTC_THRESHOLD = float(BTC_THRESHOLD_STRING)
except ValueError:
    logging.error(f"Invalid BTC_THRESHOLD value: {BTC_THRESHOLD_STRING}. Using default value 10.")
    BTC_THRESHOLD = 10.0

# Set OpenAI key and API endpoint
openai.api_key = OPENAI_API_SECRET_KEY
if OPENAI_BASE_API_URL:
    openai.api_base = OPENAI_BASE_API_URL

logging.debug(f"Using OpenAI API base URL: {openai.api_base}")

def check_large_transfers(coin_id, threshold):
    url = f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': '1'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        transactions = response.json().get('prices', [])
        large_transactions = []
        for tx in transactions:
            value = tx[1]  # Assuming value is in the second position
            if value >= threshold:
                tx_info = f'Large {coin_id.upper()} Transaction: Time: {datetime.fromtimestamp(tx[0]/1000)}, Value: {value} USD'
                logging.info(tx_info)
                large_transactions.append(tx_info)
        return large_transactions
    except requests.RequestException as e:
        logging.error(f"Error fetching {coin_id} transactions: {e}")
        return []

def send_message_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_notification": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logging.error(f"Failed to send message to Telegram: {e}")
        return False

def process_with_gpt(real_url):
    try:
        logging.debug(f"Processing URL with GPT: {real_url}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": real_url}]
        )
        return response.choices[0].message['content']
    except openai.OpenAIError as e:
        logging.error(f"Error processing with GPT: {e}")
        return None

def check_and_log_data():
    eth_transactions = check_large_transfers('ethereum', ETH_THRESHOLD)
    btc_transactions = check_large_transfers('bitcoin', BTC_THRESHOLD)

    if not eth_transactions and not btc_transactions:
        logging.info("No large transactions, skipping further processing.")
        return

    new_data_json = json.dumps({
        'ethereum': eth_transactions,
        'bitcoin': btc_transactions
    }, indent=2)

    try:
        if os.path.exists("news_transfers.txt"):
            with open("news_transfers.txt", 'r') as file:
                existing_data_json = file.read()
        else:
            existing_data_json = ""

        if new_data_json == existing_data_json:
            logging.info("No changes in transaction data, skipping further processing.")
        else:
            with open("news_transfers.txt", 'w') as file:
                file.write(new_data_json)

            news_file_url = 'https://raw.githubusercontent.com/sdlkhfksl/crypto-data-analysis/main/news_transfers.txt'
            gpt_content = process_with_gpt(news_file_url)
            if gpt_content:
                if send_message_to_telegram(gpt_content):
                    logging.info("Message sent to Telegram successfully.")
                with open("processed.txt", 'a') as file:
                    file.write(f"\nTimestamp: {datetime.now()}\n")
                    file.write(gpt_content)
                    file.write("\n" + "-"*80 + "\n")
            else:
                logging.error("Failed to process data with GPT.")
    except Exception as e:
        logging.error(f"Error during check and log data process: {e}")

if __name__ == "__main__":
    check_and_log_data()
    schedule.every(10).minutes.do(check_and_log_data)
    while True:
        schedule.run_pending()
        time.sleep(1)
