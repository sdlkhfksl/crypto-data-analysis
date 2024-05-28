import os
import feedparser
import requests
import re
import time
import logging
from collections import deque
from openai import OpenAI
from github import Github
from xml.etree import ElementTree as ET

# Configuration from environment variables
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
BASE_API_URL = os.getenv("BASE_API_URL")
GITHUB_TOKEN = os.getenv("PAT_GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
RSS_FEED_URL = 'https://cryptopanic.com/news/rss/'
PROCESSED_URLS_FILE = 'processed_urls.txt'

# OpenAI API Client Initialization
client = OpenAI(api_key=API_SECRET_KEY, base_url=BASE_API_URL)

# Deque for Tracking Processed URLs and Articles
processed_urls = deque(maxlen=50)
articles = deque(maxlen=50)

# Requests Session
session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1'

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Helper Functions
def reformat_url(url):
    """Reformat URL using regular expressions."""
    pattern = r'https://cryptopanic.com/news/(\d+)/.*'
    replacement = r'https://cryptopanic.com/news/click/\1/'
    return re.sub(pattern, replacement, url)

def get_real_url(reformatted_url):
    """Retrieve the final URL after following redirects."""
    time.sleep(10)  # Add delay
    try:
        response = session.get(reformatted_url, timeout=5)
        response.raise_for_status()
        return response.url
    except Exception as e:
        logging.error(f'Error fetching real URL: {e}')
        return reformatted_url

def fetch_rss_feed(url):
    """Fetch the RSS feed."""
    return feedparser.parse(url)

def process_url_with_openai(url, client):
    """Process URL using OpenAI's GPT model."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Generate a summary for this URL."}, {"role": "user", "content": url}],
            stream=True,
        )
        content = ""
        for chunk in response:
            if hasattr(chunk, 'choices'):
                choices = chunk.choices
                if len(choices) > 0:
                    content += choices[0].message['content']
        return content
    except Exception as e:
        logging.error(f'Error processing URL with OpenAI: {e}')
        return ""

def update_github_rss_feed(repo, articles):
    """Update the GitHub repository with the latest RSS feed."""
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "CryptoPanic News"
    ET.SubElement(channel, "link").text = "https://cryptopanic.com"
    ET.SubElement(channel, "description").text = "Latest news from CryptoPanic"
    
    for article in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article["title"]
        ET.SubElement(item, "link").text = article["link"]
        ET.SubElement(item, "pubDate").text = article["pub_date"]
        ET.SubElement(item, "description").text = article["content"]
    
    tree = ET.ElementTree(root)
    feed_content = ET.tostring(root, encoding='utf-8', method='xml').decode()
    
    try:
        contents = repo.get_contents("rss_feed.xml")
        repo.update_file(contents.path, "Update RSS feed", feed_content, contents.sha)
        logging.info("GitHub RSS feed updated successfully.")
    except Exception as e:
        logging.error(f'Error updating GitHub RSS feed: {e}')

def load_processed_urls(filename):
    """Load processed URLs from a file."""
    try:
        with open(filename, 'r') as file:
            return deque(file.read().splitlines(), maxlen=50)
    except FileNotFoundError:
        return deque(maxlen=50)

def save_processed_urls(filename, urls):
    """Save processed URLs to a file."""
    with open(filename, 'w') as file:
        for url in urls:
            file.write(url + '\n')

# Load processed URLs from file
processed_urls = load_processed_urls(PROCESSED_URLS_FILE)

# Main Processing Loop
while True:
    try:
        feed = fetch_rss_feed(RSS_FEED_URL)
        for entry in feed.entries:
            formatted_url = reformat_url(entry.link)
            final_url = get_real_url(formatted_url)
            
            if final_url and final_url not in processed_urls:
                # Process URL using OpenAI's GPT model
                content = process_url_with_openai(final_url, client)
                
                if content:
                    article = {
                        "title": entry.title,
                        "link": final_url,
                        "pub_date": entry.published,
                        "content": content
                    }
                    articles.append(article)
                    processed_urls.append(final_url)
                    
                    # Authenticate to GitHub and update the repository
                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
                    update_github_rss_feed(repo, articles)
                    
                    # Save processed URLs to file
                    save_processed_urls(PROCESSED_URLS_FILE, processed_urls)
                
                time.sleep(10)  # Rate-limit our requests

        time.sleep(60)  # Sleep before starting the next cycle
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
