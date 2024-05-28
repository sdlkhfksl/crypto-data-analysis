import os
import requests
import openai
import logging
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置API密钥
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# 发送消息到 Telegram
def send_message_to_telegram(message):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    telegram_params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    response = requests.post(telegram_url, data=telegram_params)
    return response.status_code == 200

# 读取文件内容
def read_file_content(file_path):
    with open(file_path, 'r') as file:
        return file.read()

# 合并两个文件的内容到 news.txt
def merge_files():
    economic_data = read_file_content('news_economic.txt')
    transfers_data = read_file_content('news_transfers.txt')
    
    with open('news.txt', 'w') as news_file:
        news_file.write(economic_data)
        news_file.write('\n\n')
        news_file.write(transfers_data)

# 读取 news.txt 内容并请求 ChatGPT 处理
def request_chatgpt():
    real_url = "https://raw.githubusercontent.com/sdlkhfksl/crypto-data-analysis/main/news.txt"
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Please analyze the following data: {real_url}"}
    ]
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    return response.choices[0].message['content']

# 合并、处理并发送数据到 Telegram，并记录到 processed.txt
def process_and_send_data():
    merge_files()
    
    response = request_chatgpt()
    if response:
        timestamped_response = f"{datetime.now().isoformat()}: {response}"
        
        # 发送到 Telegram
        if send_message_to_telegram(timestamped_response):
            logging.info("Message sent to Telegram successfully.")
        else:
            logging.error("Failed to send message to Telegram.")
        
        # 写入 processed.txt
        with open('processed.txt', 'a') as file:
            file.write(timestamped_response + '\n')

# 定时任务设置
schedule.every().hour.do(process_and_send_data)  # 每小时处理和发送数据

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
