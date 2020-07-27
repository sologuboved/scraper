import re
import requests
import json
from bs4 import BeautifulSoup
from pprint import pprint
from helpers import counter


class PostScraper:
    def __init__(self, post_url):
        self.post_url = post_url
        self.post = dict()
        self.comments = list()

    def scrape_post(self):
        soup = BeautifulSoup(requests.get(self.post_url).text, 'lxml')
        self.post['title'] = soup.find_all('title')[0].text
        post = process_links(soup.find_all('article', {'class': "b-singlepost-body entry-content e-content"})[0])
        self.post['post'] = BeautifulSoup(post, 'lxml').text
        self.post['date'] = soup.find_all('time', {'class': "b-singlepost-author-date published dt-published"})[0].text
        pprint(self.post)

    def scrape_threads(self):
        contents = get_contents(self.post_url)
        thread_urls = [comment['thread_url'] for comment in contents['comments']]
        count = counter(len(thread_urls))
        for thread_url in thread_urls:
            self.scrape_thread(thread_url)
            next(count)
        print()
        pprint(self.comments)

    def scrape_thread(self, thread_url):
        for comment in get_contents(thread_url)['comments']:
            try:
                curr_thread_url = comment['thread_url']
            except KeyError:
                continue
            if curr_thread_url == thread_url:
                comment = dict(zip(('author', 'text', 'date'),
                                   (comment[fieldname] for fieldname in ('commenter_journal_base',
                                                                         'article',
                                                                         'ctime'))))
                comment['thread_url'] = thread_url
                self.comments.append(comment)
                return


def get_contents(url):
    return json.loads(re.findall(
        r"Site\.page = (.+?)Site\.page\.template", requests.get(url).text, flags=re.DOTALL
    )[0].strip()[:-1])


def process_links(soup):
    soup = str(soup)
    res = re.sub(r"<a href=(.+?)>(.+?)</a>", r"[a href=\1]\2[/a]", soup, flags=re.DOTALL)
    print(res)
    return soup


if __name__ == '__main__':
    # scraper = PostScraper('https://formerchild.livejournal.com/39186.html')
    scraper = PostScraper('https://formerchild.livejournal.com/39619.html')
    # scraper = PostScraper('https://baaltii1.livejournal.com/198675.html')
    # scraper.scrape_thread('https://formerchild.livejournal.com/39619.html?thread=127939#t127939')
    # scraper.scrape_threads()
    scraper.scrape_post()
    pass
