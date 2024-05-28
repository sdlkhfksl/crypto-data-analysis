name: Run Large Transfer Monitor

on:
  schedule:
    - cron: '*/10 * * * *'  # 每10分钟运行一次
  workflow_dispatch:

jobs:
  run-large-transfer-monitor:
    runs-on: ubuntu-latest
    concurrency:
      group: openai-scripts
      cancel-in-progress: true

    steps:
    - name: Checkout code
      uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.x'

    - name: Install dependencies
      run: |
        pip install requests python-dotenv openai==1.14.2 schedule

    - name: Run Large Transfer Monitor Script
      env:
        ETHERSCAN_API_KEY: ${{ secrets.ETHERSCAN_API_KEY }}
        BLOCKCYPHER_API_KEY: ${{ secrets.BLOCKCYPHER_API_KEY }}
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        OPENAI_API_SECRET_KEY: ${{ secrets.OPENAI_API_SECRET_KEY }}
        OPENAI_BASE_API_URL: ${{ secrets.OPENAI_BASE_API_URL }}
        ETH_ADDRESS: ${{ secrets.ETH_ADDRESS }}
        BTC_ADDRESS: ${{ secrets.BTC_ADDRESS }}
        ETH_THRESHOLD: ${{ secrets.ETH_THRESHOLD }}
        BTC_THRESHOLD: ${{ secrets.BTC_THRESHOLD }}
      run: |
        python large_transfer_monitor.py
