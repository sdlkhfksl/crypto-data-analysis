import os
import requests
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import openai

# 加载环境变量
load_dotenv()

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置API密钥和其他配置信息
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OPENAI_API_SECRET_KEY = os.getenv('OPENAI_API_SECRET_KEY')
OPENAI_BASE_API_URL = os.getenv('OPENAI_BASE_API_URL')

FINNHUB_BASE_URL = 'https://finnhub.io/api/v1'
COINGECKO_URL = 'https://api.alternative.me/fng/?limit=1'
NEWS_FILE_PATH = 'news_economic.txt'
PROCESSED_FILE_PATH = 'processed.txt'

# 通用API请求函数
def get_data_from_api(endpoint, params):
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logging.error(f"Other error occurred: {err}")
    return None

# 获取实际国内生产总值（Real GDP）
def get_real_gdp():
    params = {'indicator': 'gdp', 'token': FINNHUB_API_KEY}
    return get_data_from_api(f"{FINNHUB_BASE_URL}/indicator", params)

# 获取失业率（Unemployment Rate）
def get_unemployment_rate():
    params = {'indicator': 'unemployment_rate', 'token': FINNHUB_API_KEY}
    return get_data_from_api(f"{FINNHUB_BASE_URL}/indicator", params)

# 获取通货膨胀率（Inflation Rate）
def get_inflation():
    params = {'indicator': 'inflation_rate', 'token': FINNHUB_API_KEY}
    return get_data_from_api(f"{FINNHUB_BASE_URL}/indicator", params)

# 获取消费者价格指数（CPI）
def get_cpi():
    params = {'indicator': 'cpi', 'token': FINNHUB_API_KEY}
    return get_data_from_api(f"{FINNHUB_BASE_URL}/indicator", params)

# 获取恐惧与贪婪指数（Fear & Greed Index）
def get_fear_greed_index():
    response = requests.get(COINGECKO_URL)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch Fear & Greed Index data: {response.text}")
        return None

# 发送消息到Telegram
def send_message_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_notification": True
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Failed to send message to Telegram: {e}")
        return False

# 利用OpenAI GPT模型处理数据
def process_with_gpt(real_url):
    try:
        openai.api_key = OPENAI_API_SECRET_KEY
        response = openai.Completion.create(
            engine="gpt-3.5-turbo",
            prompt=real_url,
            max_tokens=1024
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logging.error(f"Error processing with GPT: {e}")
        return None

# 检查并记录经济数据
def check_and_log_data():
    data = {
        'Real GDP': get_real_gdp(),
        'Unemployment Rate': get_unemployment_rate(),
        'Inflation Rate': get_inflation(),
        'Consumer Price Index (CPI)': get_cpi(),
        'Fear & Greed Index': get_fear_greed_index()
    }

    # 检查是否有获取不到的数据
    if any(value is None for value in data.values()):
        logging.error("Some of the economic data is None, skipping...")
        return

    new_data_json = json.dumps(data, indent=2)

    # 读取文件中的现有数据
    if os.path.exists(NEWS_FILE_PATH):
        with open(NEWS_FILE_PATH, 'r') as file:
            existing_data_json = file.read()
    else:
        existing_data_json = ""

    # 如果数据没有变化则跳过进一步处理
    if new_data_json == existing_data_json:
        logging.info("No changes in data, skipping further processing.")
    else:
        # 将新的数据写入news_economic.txt
        with open(NEWS_FILE_PATH, 'w') as file:
            file.write(new_data_json)

        # 利用OpenAI处理数据内容
        news_file_url = 'https://raw.githubusercontent.com/sdlkhfksl/crypto-data-analysis/main/news_economic.txt'
        gpt_content = process_with_gpt(news_file_url)
        if gpt_content:
            # 发送消息到Telegram
            if send_message_to_telegram(gpt_content):
                logging.info("Message sent to Telegram successfully.")

            # 追加存储处理后的数据到 processed.txt
            with open(PROCESSED_FILE_PATH, 'a') as file:
                file.write(f"\nTimestamp: {datetime.now()}\n")
                file.write(gpt_content)
                file.write("\n" + "-"*80 + "\n")
        else:
            logging.error("Failed to process data with GPT.")

if __name__ == "__main__":
    check_and_log_data()
