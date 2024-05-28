import os
import requests
import logging
import schedule
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("news_transfers.txt", mode='w'),  # 覆盖写入 news_transfers.txt
    logging.StreamHandler()
])

# 设置API密钥和监控地址
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BLOCKCYPHER_API_KEY = os.getenv('BLOCKCYPHER_API_KEY')
ETHERSCAN_BASE_URL = 'https://api.etherscan.io/api'
BLOCKCYPHER_BASE_URL = 'https://api.blockcypher.com/v1/btc/main'
ETH_ADDRESS = os.getenv('ETH_ADDRESS')
BTC_ADDRESS = os.getenv('BTC_ADDRESS')
ETH_THRESHOLD = float(os.getenv('ETH_THRESHOLD', '100'))  # 以太坊大额转账的阈值（单位：ETH）
BTC_THRESHOLD = float(os.getenv('BTC_THRESHOLD', '10'))   # 比特币大额转账的阈值（单位：BTC）

# 检查以太坊大额转账
def check_ethereum_large_transfers(address, threshold_eth):
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': 0,
        'endblock': 99999999,
        'sort': 'desc',
        'apikey': ETHERSCAN_API_KEY
    }
    response = requests.get(ETHERSCAN_BASE_URL, params=params)
    if response.status_code == 200:
        transactions = response.json().get('result', [])
        for tx in transactions:
            value_eth = int(tx['value']) / 10**18  # 将 Wei 转换为以太坊
            if value_eth >= threshold_eth:
                logging.info(f'Large ETH Transaction: From {tx["from"]} to {tx["to"]}, Value: {value_eth} ETH, Hash: {tx["hash"]}')
    else:
        logging.error(f"Error fetching Ethereum transactions: {response.status_code}")

# 检查比特币大额转账
def check_bitcoin_large_transfers(address, threshold_btc):
    url = f'{BLOCKCYPHER_BASE_URL}/addrs/{address}/full?token={BLOCKCYPHER_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        transactions = response.json().get('txs', [])
        for tx in transactions:
            for out in tx['outputs']:
                value_btc = out['value'] / 10**8  # 将 Satoshi 转换为比特币
                if value_btc >= threshold_btc:
                    logging.info(f'Large BTC Transaction: To {out["addresses"][0]}, Value: {value_btc} BTC, Hash: {tx["hash"]}')
    else:
        logging.error(f"Error fetching Bitcoin transactions: {response.status_code}")

# 设置监控任务
def monitor_large_transfers():
    logging.info('Checking Ethereum large transfers...')
    check_ethereum_large_transfers(ETH_ADDRESS, ETH_THRESHOLD)

    logging.info('Checking Bitcoin large transfers...')
    check_bitcoin_large_transfers(BTC_ADDRESS, BTC_THRESHOLD)

# 定时任务设置
schedule.every(10).minutes.do(monitor_large_transfers)  # 每10分钟检查一次大额转账

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
