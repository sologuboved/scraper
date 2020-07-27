import re
import requests
import json
from pprint import pprint


def scrape_threads(post_url):
    contents = get_contents(post_url)
    thread_urls = [comment['thread_url'] for comment in contents['comments']]
    print('Got', len(thread_urls), 'threads')
    for thread_url in thread_urls:
        scrape_thread(thread_url)
        break


def scrape_thread(thread_url):
    for comment in get_contents(thread_url)['comments']:
        try:
            curr_thread_url = comment['thread_url']
        except KeyError:
            pass
        else:
            if curr_thread_url == thread_url:
                return [comment[fieldname] for fieldname in ('commenter_journal_base', 'article', 'ctime')]


def get_contents(url):
    return json.loads(re.findall(
        r"Site\.page = (.+?)Site\.page\.template", requests.get(url).text, flags=re.DOTALL
    )[0].strip()[:-1])


if __name__ == '__main__':
    # scrape_threads('https://formerchild.livejournal.com/39619.html')
    scrape_thread('https://formerchild.livejournal.com/39619.html?thread=127939#t127939')
