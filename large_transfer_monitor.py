import os
import requests
import json
import logging
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
import openai

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
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OPENAI_API_SECRET_KEY = os.getenv('OPENAI_API_SECRET_KEY')
OPENAI_BASE_API_URL = os.getenv('OPENAI_BASE_API_URL')
ETH_THRESHOLD = float(os.getenv('ETH_THRESHOLD', '100'))  # 以太坊大额转账的阈值（单位：ETH）
BTC_THRESHOLD = float(os.getenv('BTC_THRESHOLD', '10'))   # 比特币大额转账的阈值（单位：BTC）

# 设置OpenAI密钥
openai.api_key = OPENAI_API_SECRET_KEY

# 检查最近区块链上的以太坊大额转账
def check_ethereum_large_transfers(threshold_eth):
    params = {
        'module': 'account',
        'action': 'txlistinternal',
        'startblock': 0,
        'endblock': 99999999,
        'sort': 'desc',
        'apikey': ETHERSCAN_API_KEY
    }
    response = requests.get('https://api.etherscan.io/api', params=params)
    if response.status_code == 200:
        transactions = response.json().get('result', [])
        large_transactions = []
        for tx in transactions:
            value_eth = int(tx['value']) / 10**18  # 将 Wei 转换为以太坊
            if value_eth >= threshold_eth:
                tx_info = f'Large ETH Transaction: From {tx["from"]} to {tx["to"]}, Value: {value_eth} ETH, Hash: {tx["hash"]}'
                logging.info(tx_info)
                large_transactions.append(tx_info)
        return large_transactions
    else:
        logging.error(f"Error fetching Ethereum transactions: {response.status_code}")
        return []

# 检查最近区块链上的比特币大额转账
def check_bitcoin_large_transfers(threshold_btc):
    url = f'https://api.blockcypher.com/v1/btc/main/txs/{BTC_ADDRESS}?token={BLOCKCYPHER_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        transactions = response.json().get('txs', [])
        large_transactions = []
        for tx in transactions:
            for out in tx['outputs']:
                value_btc = out['value'] / 10**8  # 将 Satoshi 转换为比特币
                if value_btc >= threshold_btc:
                    tx_info = f'Large BTC Transaction: To {out["addresses"][0]}, Value: {value_btc} BTC, Hash: {tx["hash"]}'
                    logging.info(tx_info)
                    large_transactions.append(tx_info)
        return large_transactions
    else:
        logging.error(f"Error fetching Bitcoin transactions: {response.status_code}")
        return []

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
        client = openai
        stream = client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": real_url}],
            stream=True,
        )

        content = ""
        for chunk in stream:
            if hasattr(chunk, 'choices'):
                choices = chunk.choices
                if len(choices) > 0:
                    content += choices[0].message['content']
        return content
    except Exception as e:
        logging.error(f"Error processing with GPT: {e}")
        return None

# 检查并记录大额交易数据
def check_and_log_data():
    eth_transactions = check_ethereum_large_transfers(ETH_THRESHOLD)
    btc_transactions = check_bitcoin_large_transfers(BTC_THRESHOLD)

    # 检查交易是否存在
    if not eth_transactions and not btc_transactions:
        logging.info("No large transactions, skipping further processing.")
        return

    new_data_json = json.dumps({
        'ethereum': eth_transactions,
        'bitcoin': btc_transactions
    }, indent=2)

    # 读取文件中的现有数据
    if os.path.exists("news_transfers.txt"):
        with open("news_transfers.txt", 'r') as file:
            existing_data_json = file.read()
    else:
        existing_data_json = ""

    # 如果数据没有变化则跳过进一步处理
    if new_data_json == existing_data_json:
        logging.info("No changes in transaction data, skipping further processing.")
    else:
        # 将新的数据写入news_transfers.txt
        with open("news_transfers.txt", 'w') as file:
            file.write(new_data_json)

        # 将文件URL传递给GPT处理
        news_file_url = 'https://raw.githubusercontent.com/sdlkhfksl/crypto-data-analysis/main/news_transfers.txt'
        gpt_content = process_with_gpt(news_file_url)
        if gpt_content:
            # 发送消息到Telegram
            if send_message_to_telegram(gpt_content):
                logging.info("Message sent to Telegram successfully.")

            # 追加存储处理后的数据到 processed.txt
            with open("processed.txt", 'a') as file:
                file.write(f"\nTimestamp: {datetime.now()}\n")
                file.write(gpt_content)
                file.write("\n" + "-"*80 + "\n")
        else:
            logging.error("Failed to process data with GPT.")

if __name__ == "__main__":
    check_and_log_data()
    # 调度定时任务，只在脚本运行时生效
    schedule.every(10).minutes.do(check_and_log_data)
    while True:
        schedule.run_pending()
        time.sleep(1)
