import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("news_economic.txt", mode='w'),  # Overwrite news_economic.txt
    logging.StreamHandler()
])

# Set API keys and URL
BLS_API_KEY = os.getenv('BLS_API_KEY', 'default_bls_key')  # Default value for testing or debugging
FRED_API_KEY = os.getenv('FRED_API_KEY', 'e962609971d8c5b28e51982689119f64')  # Default value for testing or debugging
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'default_telegram_token')  # Default value for testing or debugging
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'default_chat_id')  # Default value for testing or debugging

BLS_BASE_URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'
NEWS_FILE_PATH = 'news_economic.txt'

# Get Unemployment Rate
def get_unemployment_rate():
    series_id = 'LNS14000000'  # Unemployment rate series ID
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    current_year = str(datetime.now().year)
    previous_year = str(datetime.now().year - 1)
    data = json.dumps({"seriesid": [series_id], "startyear": current_year, "endyear": current_year, "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        data = response.json()
        logging.info(f"BLS API Response for {current_year}: {data}")
        if 'Results' in data and 'series' in data['Results'] and len(data['Results']['series']) > 0:
            series_data = data['Results']['series'][0]['data']
            if len(series_data) > 0:
                return series_data[0]['value']
            else:
                logging.info(f"No data for {current_year}, trying {previous_year}")
                data = json.dumps({"seriesid": [series_id], "startyear": previous_year, "endyear": previous_year, "registrationkey": BLS_API_KEY})
                response = requests.post(url, data=data, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"BLS API Response for {previous_year}: {data}")
                    if 'Results' in data and 'series' in data['Results'] and len(data['Results']['series']) > 0:
                        series_data = data['Results']['series'][0]['data']
                        if len(series_data) > 0:
                            return series_data[0]['value']
                logging.error(f"No data available for both {current_year} and {previous_year}.")
                return None
    else:
        logging.error(f"Failed to fetch Unemployment Rate data: {response.status_code} {response.text}")
        return None

# Get Real GDP
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
        data = response.json()
        logging.info(f"FRED API Response: {data}")
        if 'observations' in data and len(data['observations']) > 0:
            return data['observations'][0]['value']
    else:
        logging.error(f"Failed to fetch Real GDP data: {response.status_code} {response.text}")
        return None

# Get Consumer Price Index (CPI)
def get_cpi():
    series_id = 'CUSR0000SA0'  # CPI series ID
    url = f"{BLS_BASE_URL}"
    headers = {'Content-type': 'application/json'}
    data = json.dumps({"seriesid": [series_id], "startyear": str(datetime.now().year), "endyear": str(datetime.now().year), "registrationkey": BLS_API_KEY})
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        data = response.json()
        logging.info(f"BLS API Response: {data}")
        if 'Results' in data and 'series' in data['Results'] and len(data['Results']['series']) > 0:
            return data['Results']['series'][0]['data'][0]['value']
    else:
        logging.error(f"Failed to fetch CPI data: {response.status_code} {response.text}")
        return None

# Send message to Telegram
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

# Check and log economic data
def check_and_log_data():
    data = {
        'Unemployment Rate': get_unemployment_rate(),
        'Real GDP (FRED)': get_real_gdp(),
        'Consumer Price Index (CPI)': get_cpi()
    }

    # Check if any data is None
    for key, value in data.items():
        if value is None:
            logging.error(f"{key} data is None, skipping...")
            return

    new_data_json = json.dumps(data, indent=2)

    # Read existing data from file
    if os.path.exists(NEWS_FILE_PATH):
        with open(NEWS_FILE_PATH, 'r') as file:
            existing_data_json = file.read()
    else:
        existing_data_json = ""

    # If data has not changed, skip further processing
    if new_data_json == existing_data_json:
        logging.info("No changes in data, skipping further processing.")
    else:
        # Write new data to news_economic.txt
        with open(NEWS_FILE_PATH, 'w') as file:
            file.write(new_data_json)

        # Send message to Telegram
        if send_message_to_telegram(new_data_json):
            logging.info("Message sent to Telegram successfully.")

if __name__ == "__main__":
    check_and_log_data()
