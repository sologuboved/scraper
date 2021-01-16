import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot, ParseMode
from secrets import TOKEN, MY_CHANNEL_ID, MY_BLOG_URL


def post_to_channel(page_num):
    for url, title in scrape_blog(page_num):
        text = '<a href="{}">{}</a>'.format(url, title)
        Bot(token=TOKEN).send_message(chat_id=MY_CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
        time.sleep(10)


def scrape_blog(page_num):
    links = list()
    while page_num >= 1:
        links.extend(scrape_page(page_num))
        page_num -= 1
    return links


def scrape_page(page_num):
    links = list()
    items = BeautifulSoup(requests.get(MY_BLOG_URL.format(page_num)).content, 'lxml').find_all(
        'h2', {'class': 'entry-title'}
    )
    for item in items:
        link = item.find('a', {'href': True})
        links.append((link.get('href'), link.text))
    return reversed(links)


if __name__ == '__main__':
    post_to_channel(7)
