import os
import ccxt
import requests

# 从环境变量中获取 Telegram Bot 和新闻文本的URL
bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
telegram_api_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
news_url = "https://raw.githubusercontent.com/sdlkhfksl/fetch_news/main/articles_content.txt"

# 初始化交易所（使用Coinbase）
exchange = ccxt.coinbase()

# 获取市场数据
markets = exchange.load_markets()
symbols = [symbol for symbol in markets if '-USD' in symbol and markets[symbol]['active']]

# 获取涨幅榜前五位的标的
def top_gainers(symbols, exchange, limit=5):
    try:
        tickers = exchange.fetch_tickers(symbols)
        sorted_tickers = sorted(tickers.values(), key=lambda x: x['percentage'], reverse=True)
        top_symbols = [ticker['symbol'] for ticker in sorted_tickers[:limit]]
        return top_symbols
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return []

# 获取前一天的成交量和价格
def fetch_previous_day_data(symbol, exchange):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=2)
    previous_day = ohlcv[-2]
    previous_volume = previous_day[5]  # 第6列是成交量
    previous_close = previous_day[4]  # 第5列是收盘价
    return previous_volume, previous_close

# 检查标的是否符合条件
def check_conditions(symbol, exchange, news_content):
    try:
        ticker = exchange.fetch_ticker(symbol)
        
        # 获取前两天的成交量平均值
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=3)
        volume_sum = sum([data[5] for data in ohlcv[:-1]])  # 排除当日和前一日的成交量
        average_volume = volume_sum / 2  # 前两天的平均每天成交量
        
        # 计算相对成交量
        today_volume = ticker['quoteVolume']
        relative_volume = today_volume / average_volume
        
        # 获取昨天的流通量
        circulating_supply = ticker['info'].get('circulating_supply', None)
        if circulating_supply is None:
            return False
        
        previous_day_circulating_supply, _ = fetch_previous_day_data(symbol, exchange)
        
        # 计算流通量比
        circulating_supply_ratio = circulating_supply / previous_day_circulating_supply
        
        # 检查条件
        if relative_volume / circulating_supply_ratio > 2:
            return True
        
        return False
    except Exception as e:
        print(f"Error checking conditions for {symbol}: {e}")
        return False

# 获取币种在新闻文本中出现的次数
def get_coin_occurrences(news_content, symbols):
    coin_occurrences = {}
    for symbol in symbols:
        # 将符号转换为币种名称（例如，'BTC-USD' 转换为 'BTC'）
        coin_name = symbol.split('-')[0]
        occurrences = news_content.count(coin_name)
        coin_occurrences[symbol] = occurrences
    return coin_occurrences

# 请求新闻文本
response = requests.get(news_url)
news_content = response.text

# 获取涨幅榜前五位的标的
top_symbols = top_gainers(symbols, exchange)

# 获取币种在新闻文本中出现的次数
coin_occurrences = get_coin_occurrences(news_content, top_symbols)

# 符合条件的标的
selected_symbols = [symbol for symbol in top_symbols if check_conditions(symbol, exchange, news_content) and coin_occurrences.get(symbol, 0) > 20]

# 发送满足条件的结果到 Telegram Bot
if selected_symbols:
    message = "满足条件的标的：\n" + "\n".join(selected_symbols)
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    requests.post(telegram_api_url, json=payload)
