import requests
import feedparser
import pandas as pd
from datetime import datetime
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
import os
from readability import Document
from html.parser import HTMLParser
from bs4 import BeautifulSoup
import schedule
import time

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置环境变量中的敏感信息
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RSS_FEED_URL = os.getenv('RSS_FEED_URL')

# 初始化NLP工具
nlp = spacy.load("en_core_web_sm")
analyzer = SentimentIntensityAnalyzer()

# A simple HTML parser to remove HTML tags and retrieve text content
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return "".join(self.text)

# Use readability to fetch and parse article, then use MLStripper to clean HTML tags.
def fetch_article_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f'Error fetching the article: {e}')
        return None, None, None

    doc = Document(response.text)
    s = MLStripper()
    s.feed(doc.title())
    title = s.get_data()
    s = MLStripper()
    s.feed(doc.summary())
    content = s.get_data()

    # Use BeautifulSoup to find the publication date
    soup = BeautifulSoup(response.text, 'html.parser')
    pub_date = find_publication_date(soup)

    formatted_content = f'Title: {title}\nPublication Date: {pub_date}\n\n{content}'
    return title, content, pub_date

def find_publication_date(soup):
    # Search for common publication date tags
    date_tags = ['time', 'span', 'p', 'div']
    for tag in date_tags:
        for element in soup.find_all(tag):
            if element.has_attr('datetime'):
                return element['datetime']
            if element.has_attr('class'):
                if 'date' in element['class'] or 'time' in element['class']:
                    return element.text
    # If no date found, return current date for reference
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 解析RSS feed并获取文章链接
def fetch_article_links(feed_url):
    try:
        feed_content = requests.get(feed_url).content
        feed = feedparser.parse(feed_content)
        return [entry.link for entry in feed.entries]
    except Exception as e:
        logging.error(f'Error fetching RSS feed: {e}')
        return []

# Analyze sentiment using VADER
def analyze_sentiment(text):
    return analyzer.polarity_scores(text)['compound']

# Perform Named Entity Recognition (NER)
def extract_entities(text):
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

# 生成投资信号
def generate_signal(sentiment_score, title, content, keywords):
    for keyword in keywords:
        if keyword in title.lower() or keyword in content.lower():
            if sentiment_score > 0.5:
                return "Strong Buy"
            elif sentiment_score < -0.5:
                return "Strong Sell"
            else:
                return "Neutral"
    return "Ignore"

# 扩展关键词库，包括加密货币、机构和名人
keywords = [
    "bitcoin", "btc", "ethereum", "eth", "dogecoin", "doge", "uniswap", "shiba-inu", "shib", "ripple", "xrp", 
    "binancecoin", "bnb", "cardano", "ada", "worldcoin-wld", "solana", "sol", "avalanche-2", "avax", "polkadot", 
    "dot", "the-open-network", "ton", "regulation", "policy", "government", "ban", "legal", "law", "approval", 
    "tax", "sanction", "sec", "cftc", "elon musk", "whale transfer", "whale transaction"
]

# 发送消息到Telegram
def send_message_to_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'disable_notification': True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info('Message sent to Telegram successfully.')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error sending message to Telegram: {e}')

# 存储处理过的链接
def store_processed_links(processed_articles):
    try:
        with open('processed_links.txt', 'a', encoding='utf-8') as file:
            for link in processed_articles:
                file.write(link + '\n')
    except Exception as e:
        logging.error(f'Error storing processed links: {e}')

# 检查是否已处理过的链接
def is_processed(link):
    if not os.path.exists('processed_links.txt'):
        return False
    with open('processed_links.txt', 'r', encoding='utf-8') as file:
        processed_links = file.read().splitlines()
    return link in processed_links

# 主函数
def main():
    links_file_url = RSS_FEED_URL

    links = fetch_article_links(links_file_url)
    if not links:
        return

    processed_articles = []

    for url in links:
        if is_processed(url):
            logging.info(f'Skipping already processed article: {url}')
            continue

        logging.info(f'Fetching content for: {url}')
        title, content, pub_date = fetch_article_content(url)
        if content:
            sentiment_score = analyze_sentiment(content)
            signal = generate_signal(sentiment_score, title, content, keywords)
            if signal in ["Strong Buy", "Strong Sell"]:
                entities = extract_entities(content)
                message = (f"Title: {title}\nPublication Date: {pub_date}\nContent: {content}\n"
                           f"Signal: {signal}\nEntities: {entities}\nSource: {url}")
                send_message_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
                logging.info(f"Processed article: {title}")
                processed_articles.append(url)

    store_processed_links(processed_articles)

# 定时任务调度
schedule.every(30).minutes.do(main)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
