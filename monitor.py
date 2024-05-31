import requests
import time
import os

# 获取所有加密货币的ID和名称
def get_all_coins():
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching coin list: {e}")
        return []

# 获取某些加密货币的当前价格
def get_coin_prices(coin_ids):
    ids = ",".join(coin_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching coin prices: {e}")
        return {}

# 分批获取所有币种的价格
def get_all_coin_prices(coin_ids, batch_size=100):
    all_prices = {}
    for i in range(0, len(coin_ids), batch_size):
        batch_ids = coin_ids[i:i + batch_size]
        prices = get_coin_prices(batch_ids)
        all_prices.update(prices)
    return all_prices

# 发送消息到Telegram
def send_telegram_message(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error sending message to Telegram: {e}")

# 监控价格变化
def monitor_price_changes(interval=60, threshold=0.05):
    coins = get_all_coins()
    price_history = {}
    coin_ids = [coin['id'] for coin in coins]

    while True:
        coin_prices = get_all_coin_prices(coin_ids)
        
        for coin in coins:
            coin_id = coin['id']
            current_price = coin_prices.get(coin_id, {}).get('usd', None)

            if current_price is not None:
                if coin_id not in price_history:
                    price_history[coin_id] = []
                
                price_history[coin_id].append(current_price)
                
                if len(price_history[coin_id]) > 5:
                    price_history[coin_id].pop(0)
                
                if len(price_history[coin_id]) == 5:
                    initial_price = price_history[coin_id][0]
                    price_change = (current_price - initial_price) / initial_price

                    if price_change > threshold:
                        message = f"Coin {coin['name']} ({coin['symbol']}) has increased by {price_change * 100:.2f}% in the last 5 minutes."
                        print(message)
                        send_telegram_message(message)
                    elif price_change < -threshold:
                        message = f"Coin {coin['name']} ({coin['symbol']}) has decreased by {price_change * 100:.2f}% in the last 5 minutes."
                        print(message)
                        send_telegram_message(message)
        
        time.sleep(interval)

if __name__ == "__main__":
    monitor_price_changes()
