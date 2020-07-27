import re
import requests
import json
from bs4 import BeautifulSoup
from helpers import which_watch, counter, dump_utf_json


class PostScraper:
    def __init__(self, post_url, target_json=None):
        self.post_url = post_url
        self.target_json = target_json
        self.post = dict()
        self.comments = list()

    @which_watch
    def launch(self):
        print("Launching @ {}...".format(self.post_url))
        self.scrape_post()
        self.scrape_comments()
        post = {'post': self.post, 'comments': self.comments}
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

    def scrape_comments(self):
        print("Scraping comments...")
        contents = get_contents(self.post_url)
        thread_urls = [comment['thread_url'] for comment in contents['comments']]
        count = counter(len(thread_urls))
        for thread_url in thread_urls:
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


if __name__ == '__main__':
    # scraper = PostScraper('https://formerchild.livejournal.com/39186.html')
    scraper = PostScraper('https://formerchild.livejournal.com/39619.html', 'VV_formerchild.json')
    # scraper = PostScraper('https://baaltii1.livejournal.com/198675.html')
    # scraper.scrape_comment('https://formerchild.livejournal.com/39619.html?thread=127939#t127939')
    # scraper.scrape_comments()
    # scraper.scrape_post()
    print(scraper.launch())
