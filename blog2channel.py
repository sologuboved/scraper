from pprint import pprint
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot, ParseMode
from userinfo import TOKEN, MY_CHANNEL_ID, MY_BLOG_URL, MY_BLOG_PAGE_URL


def post_to_channel(scraper):
    for url, title in scraper():
        text = '<a href="{}">{}</a>'.format(url, title)
        Bot(token=TOKEN).send_message(chat_id=MY_CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
        time.sleep(10)


def scrape_blog_from_page(page_num):
    links = list()
    while page_num >= 1:
        print(page_num)
        links.extend(scrape_page(page_num))
        page_num -= 1
    print(f"Scraped {len(links)} links")
    pprint(links)
    return links


def scrape_page(page_num):
    links = list()
    items = BeautifulSoup(requests.get(MY_BLOG_PAGE_URL.format(page_num)).content, 'lxml').find_all(
        'h2', {'class': 'entry-title'}
    )
    for item in items:
        link = item.find('a', {'href': True})
        links.append((link.get('href'), link.text))
    return reversed(links)


def scrape_blog_from_entry(entry_url):
    entry_url = MY_BLOG_URL.format(entry_url)
    links = [(
        entry_url,
        BeautifulSoup(requests.get(entry_url).content, 'lxml').find('h1', {'class': 'entry-title'}).text.strip()
    )]
    next_url = entry_url
    while True:
        print(next_url)
        try:
            next_entry = BeautifulSoup(requests.get(next_url).content, 'lxml').find(
                'div', {'class': 'nav-next'}
            ).find('a', {'href': True})
        except AttributeError:
            break
        next_url = next_entry.get('href')
        links.append((next_url, next_entry.text.split("Next post")[-1].strip()))
        time.sleep(2)
    print(f"Scraped {len(links)} links")
    pprint(links)
    return links


if __name__ == '__main__':
    # from functools import partial
    # from userinfo import MY_BLOG_URL
    # post_to_channel(partial(scrape_blog_from_page, 7))
    # post_to_channel(partial(scrape_blog_from_entry,
    #                         MY_BLOG_URL.format('2021/09/10/eilenberger-on-heidegger-and-ecology/')))
    pass
