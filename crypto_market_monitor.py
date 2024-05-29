import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
import json

# 加载环境变量
load_dotenv()

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置API密钥和URL
BLS_API_KEY = os.getenv('BLS_API_KEY')
FRED_API_KEY = os.getenv('FRED_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

BLS_BASE_URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'
NEWS_FILE_PATH = 'news_economic.txt'
PROCESSED_FILE_PATH = 'processed.txt'

# 获取失业率（最新的Unemployment Rate）
def get_unemployment_rate():
    series_id = 'LNS14000000'  # 失业率系列ID
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    data = json.dumps({"seriesid": [series_id], "startyear": str(datetime.now().year), "endyear": str(datetime.now().year), "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'Results' in data and 'series' in data['Results'] and len(data['Results']['series']) > 0:
            return data['Results']['series'][0]['data'][0]['value']
    else:
        logging.error(f"Failed to fetch Unemployment Rate data: {response.text}")
        return None

# 获取实际国内生产总值（最新的Real GDP）
def get_real_gdp():
    params = {
        'series_id': 'GDPC1',
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'realtime_start': '2024-01-01',
        'realtime_end': '2024-12-31',
        'limit': 1,
        'sort_order': 'desc'
    }
    response = requests.get(FRED_BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'observations' in data and len(data['observations']) > 0:
            return data['observations'][-1]['value']
    else:
        logging.error(f"Failed to fetch Real GDP data: {response.text}")
        return None

# 获取消费者价格指数（最新的CPI）
def get_cpi():
    series_id = 'CUSR0000SA0'   # CPI系列ID
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    data = json.dumps({"seriesid": [series_id], "startyear": str(datetime.now().year), "endyear": str(datetime.now().year), "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'Results' in data and 'series' in data['Results'] and len(data['Results']['series']) > 0:
            return data['Results']['series'][0]['data'][0]['value']
    else:
        logging.error(f"Failed to fetch CPI data: {response.text}")
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

# 检查并记录经济数据
def check_and_log_data():
    data = {
        'Unemployment Rate': get_unemployment_rate(),
        'Real GDP (FRED)': get_real_gdp(),
        'Consumer Price Index (CPI)': get_cpi()
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

        # 发送消息到Telegram
        if send_message_to_telegram(new_data_json):
            logging.info("Message sent to Telegram successfully.")

if __name__ == "__main__":
    check_and_log_data()
