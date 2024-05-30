import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("news_economic_log.txt", mode='a'),  # Append to log file
    logging.StreamHandler()
])

# Ensure that the news_economic.txt file exists and initialize if empty or corrupt
def initialize_data_file():
    if not os.path.exists("news_economic.txt") or os.path.getsize("news_economic.txt") == 0:
        logging.info("Initializing news_economic.txt with empty data structure.")
        with open("news_economic.txt", 'w') as file:
            empty_data = {
                "Unemployment Rate": {"value": None, "date": None},
                "Real GDP (FRED)": {"value": None, "date": None},
                "Consumer Price Index (CPI)": {"value": None, "date": None},
                "Fed Interest Rate Policy": {"value": None, "date": None},
                "Producer Price Index (PPI)": {"value": None, "date": None},
                "Non-Farm Payroll Report": {"value": None, "date": None},
                "Retail Sales Data": {"value": None, "date": None},
                "Fear and Greed Index": {"value": None, "date": None},
            }
            json.dump(empty_data, file, ensure_ascii=False, indent=4)
        logging.info("news_economic.txt initialized successfully.")

initialize_data_file()

# Set API keys and URLs
BLS_API_KEY = os.getenv('BLS_API_KEY', 'default_bls_key')
FRED_API_KEY = os.getenv('FRED_API_KEY', 'default_fred_key')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'default_telegram_token')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'default_chat_id')
FEAR_GREED_INDEX_API = "https://api.alternative.me/fng/?limit=1"

BLS_BASE_URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'
NEWS_FILE_PATH = 'news_economic.txt'

# Helper function to get the current time in UTC+8
def get_utc_plus_8_time():
    utc_plus_8 = timezone(timedelta(hours=8))
    return datetime.now(utc_plus_8).strftime("%Y-%m-%d %H:%M:%S")

# Helper function to send message to Telegram
def send_message_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_notification": True
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info("Message sent to Telegram successfully.")
        else:
            logging.error(f"Failed to send message to Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Error sending message to Telegram: {e}")

# Fetch data functions for various indicators
def get_unemployment_rate():
    series_id = 'LNS14000000'
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    current_year = str(datetime.now().year)
    data = json.dumps({"seriesid": [series_id], "startyear": current_year, "endyear": current_year, "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if 'Results' in result and 'series' in result['Results'] and len(result['Results']['series']) > 0:
            series_data = result['Results']['series'][0]['data']
            if len(series_data) > 0:
                logging.info("Unemployment Rate fetched successfully.")
                return float(series_data[0]['value']), f"{series_data[0]['year']}年 {series_data[0]['periodName']}"
    logging.error(f"Failed to fetch Unemployment Rate data: {response.status_code} {response.text}")
    return None, None

def get_real_gdp():
    params = {
        'series_id': 'GDPC1',
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'limit': 1,
        'sort_order': 'desc'
    }
    response = requests.get(FRED_BASE_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        if 'observations' in result and len(result['observations']) > 0:
            logging.info("Real GDP fetched successfully.")
            return float(result['observations'][0]['value']), result['observations'][0]['date']
    logging.error(f"Failed to fetch Real GDP data: {response.status_code} {response.text}")
    return None, None

def get_cpi():
    series_id = 'CUSR0000SA0'
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    data = json.dumps({"seriesid": [series_id], "startyear": str(datetime.now().year), "endyear": str(datetime.now().year), "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if 'Results' in result and 'series' in result['Results'] and len(result['Results']['series']) > 0:
            series_data = result['Results']['series'][0]['data']
            if len(series_data) > 0:
                logging.info("CPI fetched successfully.")
                return float(series_data[0]['value']), f"{series_data[0]['year']}年 {series_data[0]['periodName']}"
    logging.error(f"Failed to fetch CPI data: {response.status_code} {response.text}")
    return None, None

def get_fed_interest_rate():
    params = {
        'series_id': 'FEDFUNDS',
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'limit': 1,
        'sort_order': 'desc'
    }
    response = requests.get(FRED_BASE_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        if 'observations' in result and len(result['observations']) > 0:
            logging.info("Fed Interest Rate fetched successfully.")
            return float(result['observations'][0]['value']), result['observations'][0]['date']
    logging.error(f"Failed to fetch Fed Interest Rate data: {response.status_code} {response.text}")
    return None, None

def get_ppi():
    series_id = 'WPU00000000'
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    data = json.dumps({"seriesid": [series_id], "startyear": str(datetime.now().year), "endyear": str(datetime.now().year), "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if 'Results' in result and 'series' in result['Results'] and len(result['Results']['series']) > 0:
            series_data = result['Results']['series'][0]['data']
            if len(series_data) > 0:
                logging.info("PPI fetched successfully.")
                return float(series_data[0]['value']), f"{series_data[0]['year']}年 {series_data[0]['periodName']}"
    logging.error(f"Failed to fetch PPI data: {response.status_code} {response.text}")
    return None, None

def get_non_farm_payroll():
    series_id = 'CES0000000001'
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    data = json.dumps({"seriesid": [series_id], "startyear": str(datetime.now().year), "endyear": str(datetime.now().year), "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if 'Results' in result and 'series' in result['Results'] and len(result['Results']['series']) > 0:
            series_data = result['Results']['series'][0]['data']
            if len(series_data) > 0:
                logging.info("Non-Farm Payroll fetched successfully.")
                return float(series_data[0]['value']), f"{series_data[0]['year']}年 {series_data[0]['periodName']}"
    logging.error(f"Failed to fetch Non-Farm Payroll data: {response.status_code} {response.text}")
    return None, None

def get_retail_sales():
    params = {
        'series_id': 'RSAFS',
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'limit': 1,
        'sort_order': 'desc'
    }
    response = requests.get(FRED_BASE_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        if 'observations' in result and len(result['observations']) > 0:
            logging.info("Retail Sales fetched successfully.")
            return float(result['observations'][0]['value']), result['observations'][0]['date']
    logging.error(f"Failed to fetch Retail Sales data: {response.status_code} {response.text}")
    return None, None

def get_fear_greed_index():
    response = requests.get(FEAR_GREED_INDEX_API)
    if response.status_code == 200:
        result = response.json()
        if 'data' in result and len(result['data']) > 0:
            logging.info("Fear and Greed Index fetched successfully.")
            return int(result['data'][0]['value']), result['data'][0]['timestamp']
    logging.error(f"Failed to fetch Fear and Greed Index data: {response.status_code} {response.text}")
    return None, None

# Check and log economic data
def check_and_log_data():
    prev_data = {}
    # Read previous data from file if exists
    if os.path.exists(NEWS_FILE_PATH) and os.path.getsize(NEWS_FILE_PATH) > 0:
        try:
            with open(NEWS_FILE_PATH, 'r') as file:
                prev_data = json.load(file)
                logging.info("Previous data loaded successfully.")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse previous data file: {e}")
            prev_data = {}  # Reset to empty if parsing fails
    else:
        logging.info("news_economic.txt does not exist or is empty, initializing with empty data structure.")
        
    # Fetch current data
    indicators = {
        'Unemployment Rate': get_unemployment_rate(),
        'Real GDP (FRED)': get_real_gdp(),
        'Consumer Price Index (CPI)': get_cpi(),
        'Fed Interest Rate Policy': get_fed_interest_rate(),
        'Producer Price Index (PPI)': get_ppi(),
        'Non-Farm Payroll Report': get_non_farm_payroll(),
        'Retail Sales Data': get_retail_sales(),
        'Fear and Greed Index': get_fear_greed_index()
    }

    updated_indicators = []  # To keep track of updated indicators

    # Define the influence of each indicator
    influence = {
        'Unemployment Rate': {
            'increase': "行情利空，对币市看空 😔",
            'decrease': "行情利好，对币市看多 🙂"
        },
        'Real GDP (FRED)': {
            'increase': "对经济有利，风险较大，对币市看多 🙂",
            'decrease': "对经济不利，风险较大，对币市看空 😔"
        },
        'Consumer Price Index (CPI)': {
            'increase': "对抗通胀有利，对币市看多 🙂",
            'decrease': "通胀减少无明显影响 😐"
        },
        'Fed Interest Rate Policy': {
            'increase': "利率上升，对币市看空 😔",
            'decrease': "利率下降，对币市看多 🙂"
        },
        'Producer Price Index (PPI)': {
            'increase': "对抗通胀有利，对币市看多 🙂",
            'decrease': "生产成本下降无明显影响 😐"
        },
        'Non-Farm Payroll Report': {
            'increase': "就业增加，对币市看多 🙂",
            'decrease': "就业减少，对币市看空 😔"
        },
        'Retail Sales Data': {
            'increase': "消费增加，对币市看多 🙂",
            'decrease': "消费减少，对币市看空 😔"
        },
        'Fear and Greed Index': {
            'increase': "市场恐惧减弱，对币市看多 🙂",
            'decrease': "市场恐惧增强，对币市看空 😔"
        }
    }

    # Compare current data with previous data and send updates
    new_data = {}
    for key, (current_value, date) in indicators.items():
        if current_value is not None:
            new_data[key] = {
                'value': current_value,
                'date': date
            }
            prev_value = prev_data.get(key, {}).get('value')
            if prev_value is not None:
                direction = "increase" if current_value > prev_value else "decrease"
            else:
                direction = "increase"  # Treat as increase if there is no previous value

            impact = influence[key][direction]

            timestamp = get_utc_plus_8_time()
            prev_value_display = prev_value if prev_value is not None else '无记录的'
            change_message = f"{key} 更新: 由 {prev_value_display} 变为 {current_value} ({'📈 增加' if direction == 'increase' else '📉 减少'}, {impact})"
            
            send_message_to_telegram(change_message)
            logging.info(change_message)

            updated_indicators.append(key)

    # Update the data file
    logging.info("Updating news_economic.txt with new data.")
    with open(NEWS_FILE_PATH, 'w') as file:
        json.dump(new_data, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    check_and_log_data()
