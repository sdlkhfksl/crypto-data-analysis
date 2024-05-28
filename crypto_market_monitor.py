import requests
import time
import logging
import schedule
from datetime import datetime

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_KEY = 'YOUR_API_KEY'
BASE_URL = 'https://www.alphavantage.co/query'
FEAR_GREED_URL = 'https://api.alternative.me/fng/?limit=1'

# 获取实际国内生产总值（Real GDP）
def get_real_gdp():
    params = {
        'function': 'REAL_GDP',
        'interval': 'annual',
        'apikey': API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

# 获取失业率（Unemployment Rate）
def get_unemployment_rate():
    params = {
        'function': 'UNEMPLOYMENT',
        'interval': 'monthly',
        'apikey': API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

# 获取通货膨胀率（Inflation Rate）
def get_inflation():
    params = {
        'function': 'INFLATION',
        'apikey': API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

# 获取消费者价格指数（CPI）
def get_cpi():
    params = {
        'function': 'CPI',
        'interval': 'monthly',
        'apikey': API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

# 获取恐惧与贪婪指数（Fear & Greed Index）
def get_fear_greed_index():
    response = requests.get(FEAR_GREED_URL)
    return response.json()

# 获取VIX指数（Volatility Index）
def get_vix():
    params = {
        'function': 'VIX',
        'interval': 'daily',
        'apikey': API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    return response.json()

# 检查并记录数据
def check_and_log_data():
    indicators = {
        'Real GDP': get_real_gdp,
        'Unemployment Rate': get_unemployment_rate,
        'Inflation Rate': get_inflation,
        'Consumer Price Index (CPI)': get_cpi,
        'Fear & Greed Index': get_fear_greed_index,
        'Volatility Index (VIX)': get_vix
    }
    
    for name, func in indicators.items():
        logging.info(f'Fetching {name} data...')
        
        try:
            data = func()
            logging.info(f'{name} Data:')
            logging.info(data)
        except Exception as e:
            logging.error(f'Error fetching {name}: {e}')
        
        logging.info('\n' + '-'*80 + '\n')

# 定时任务设置
schedule.every(1).hours.do(check_and_log_data)  # 每小时检查和记录一次

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
