import re
import requests
import json
from pprint import pprint
from bs4 import BeautifulSoup
from helpers import which_watch, counter, dump_utf_json


class PostScraper:
    def __init__(self, post_url, target_json=None):
        self.post_url = post_url
        self.target_json = target_json
        self.thread_urls = set()
        self.post = dict()
        self.comments = list()

    @which_watch
    def launch(self):
        print("Launching @ {}...".format(self.post_url))
        self.scrape_post()
        self.scrape_pages()
        self.scrape_comments()
        post = {'url': self.post_url, 'post': self.post, 'comments': self.comments}
        if self.target_json:
            dump_utf_json(post, self.target_json)
        return post

    def scrape_post(self):
        print("Scraping post...")
        soup = BeautifulSoup(requests.get(self.post_url).text, 'lxml')
        self.post['title'] = soup.find_all('title')[0].text
        self.post['date'] = soup.find_all('time', {'class': "b-singlepost-author-date published dt-published"})[0].text
        self.post['post'] = process_links(
            soup.find_all('article', {'class': "b-singlepost-body entry-content e-content"})[0]
        )

    def scrape_pages(self):
        print("Scraping pages...")
        try:
            num_pages = max(
                int(item.text) for item in BeautifulSoup(
                    requests.get(self.post_url).text, 'lxml'
                ).find_all('li', {'class': 'b-pager-page'}) if item is not None
            )
        except ValueError:
            num_pages = 1
        print("...{} pages found".format(num_pages))
        for page_num in range(1, num_pages + 1):
            self.scrape_thread_urls(self.post_url + '?page={}'.format(page_num))

    def scrape_thread_urls(self, page_url):
        print("Scraping thread URLs from {}...".format(page_url))
        thread_pattern = re.compile(get_thread_pattern(self.post_url))
        thread_urls = list(set(thread_pattern.findall(requests.get(page_url).text)))
        while thread_urls:
            curr_thread_url = thread_urls.pop(0)
            if curr_thread_url in self.thread_urls:
                continue
            curr_thread = requests.get(curr_thread_url).text
            for thread_url in set(thread_pattern.findall(curr_thread)) - self.thread_urls - set(thread_urls):
                if thread_url not in thread_urls:
                    thread_urls.append(thread_url)
            self.thread_urls.add(curr_thread_url)
        print("Currently {} thread urls".format(len(self.thread_urls)))

    def scrape_comments(self):
        print("Scraping comments...")
        count = counter(len(self.thread_urls))
        for thread_url in self.thread_urls:
            self.scrape_comment(thread_url)
            next(count)
        print()

    def scrape_comment(self, thread_url):
        for comment in get_contents(thread_url)['comments']:
            try:
                curr_thread_url = comment['thread_url']
            except KeyError:
                continue
            if curr_thread_url == thread_url:
                self.comments.append({
                    'thread_url': thread_url,
                    'author': comment['commenter_journal_base'],
                    'date': comment['ctime'],
                    'text': process_links(comment['article'])
                })
                return


def get_contents(url):
    return json.loads(re.findall(
        r"Site\.page = (.+?)Site\.page\.template", requests.get(url).text, flags=re.DOTALL
    )[0].strip()[:-1])


def process_links(text):
    return BeautifulSoup(
        re.sub(r"<a href=(.+?)>(.+?)</a>", r"[a href=\1]\2[/a]", str(text), flags=re.DOTALL), 'lxml'
    ).text


def get_thread_pattern(url):
    return '(' + url.replace('.', r'\.') + r'\?thread=\d+?#t\d+?)"'


if __name__ == '__main__':
    # scraper = PostScraper('https://bohemicus.livejournal.com/144237.html')
    # scraper = PostScraper('https://formerchild.livejournal.com/39619.html')
    scraper = PostScraper('https://formerchild.livejournal.com/39619.html', 'VV_formerchild.json')
    # scraper = PostScraper('https://baaltii1.livejournal.com/198675.html')
    # scraper.scrape_comment('https://formerchild.livejournal.com/39619.html?thread=127939#t127939')
    # scraper.scrape_comments2()
    # scraper.scrape_comments()
    # scraper.scrape_post()
    scraper.launch()
    # scraper.scrape_pages()
