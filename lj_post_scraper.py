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
        self.unavailable_comments = list()

    @which_watch
    def launch(self):
        print("Launching @ {}...".format(self.post_url))
        self.get_target()
        self.scrape_post()
        self.scrape_pages()
        self.scrape_comments()
        post = {'url': self.post_url,
                'post': self.post,
                'comments': sorted(self.comments, key=lambda c: c['thread_url'])}
        if self.target_json:
            dump_utf_json(post, self.target_json)
        return post

    def get_target(self):
        if not self.target_json:
            self.target_json = '{}_{}.json'.format(
                *re.findall(r'https://(.+?)\..+?/(\d+?)\.html', self.post_url, flags=re.DOTALL)[0]
            )
        print("Target will be", self.target_json)

    def scrape_post(self):
        raise NotImplementedError

    def scrape_pages(self):
        print("Scraping pages...")
        page_stub = '{}?page={{}}'.format(self.post_url)
        req = requests.get(self.post_url).text
        num_pages = 1
        while True:
            if page_stub.format(num_pages + 1) not in req:
                break
            num_pages += 1
        print("...{} page(s) found".format(num_pages))
        for page_num in range(1, num_pages + 1):
            self.scrape_thread_urls(page_stub.format(page_num))

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
        print("\nScraped {} comments. {} comments proved unavailable:".format(len(self.comments),
                                                                             len(self.unavailable_comments)))
        for thread_url in self.unavailable_comments:
            print(thread_url)

    def scrape_comment(self, thread_url):
        raise NotImplementedError


class NewStyle(PostScraper):
    def __init__(self, post_url, target_json=None):
        super().__init__(post_url, target_json)

    def scrape_post(self):
        print("Scraping post...")
        soup = BeautifulSoup(requests.get(self.post_url).text, 'lxml')
        self.post['title'] = soup.find_all('title')[0].text
        self.post['date'] = soup.find_all('time', {'class': "b-singlepost-author-date published dt-published"})[0].text
        self.post['post'] = fix_links(
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
        print("...{} page(s) found".format(num_pages))
        for page_num in range(1, num_pages + 1):
            self.scrape_thread_urls(self.post_url + '?page={}'.format(page_num))

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
                    'text': fix_links(comment['article'])
                })
                return


class OldStyle(PostScraper):
    def __init__(self, post_url, target_json=None):
        super().__init__(post_url, target_json)

    def scrape_post(self):
        print("Scraping post...")
        soup = BeautifulSoup(requests.get(self.post_url).content, 'lxml')
        self.post['title'] = soup.find_all('title')[0].text
        self.post['date'] = soup.find_all('dd', {'class': 'entry-date'})[0].text
        self.post['post'] = fix_links(soup.find_all('div', {'class': "entry-content"})[0])

    def scrape_comment(self, thread_url):
        soup = BeautifulSoup(requests.get(thread_url).content, 'lxml')
        info = soup.find_all('div', {'class': 'comment-wrap'})[0]
        if "Deleted comment" in str(info):
            self.unavailable_comments.append(thread_url)
            return
        try:
            author = info.find_all(
                'div', {'class': 'comment-poster-info'}
            )[0]
        except IndexError:
            author = None
        else:
            try:
                author = author.find_all(
                    'a', {'class': 'i-ljuser-username'}
                )[0].get('href')
            except IndexError:
                try:
                    author = author.find_all(
                        'div', {'class': "ljuser i-ljuser i-ljuser-deleted i-ljuser-type-P"}
                    )[0].get('href')
                except IndexError:  # https://baaltii1.livejournal.com/198675.html?thread=4818195#t4818195
                    author = None
        date = None
        for item in info.find_all('span', {'title': True}):
            item = item.text
            if re.match(r'^\d\d\d\d-\d\d-\d\d', item):
                date = item
                break
        try:
            title = fix_links(info.find_all('div', {'class': 'comment-head-in'})[0].find_all('h3')[0]).strip()
        except IndexError:
            title = None
        try:
            text = info.find_all('div', {'class': "comment-text j-c-resize-images"})[0]
        except IndexError:
            try:
                text = info.find_all('div', {'class': "comment-text j-c-resize-images comment-text-cwoup"})[0]
            except IndexError:
                self.unavailable_comments.append(thread_url)
                return
        text = fix_links(text)
        self.comments.append({'thread_url': thread_url, 'author': author, 'date': date, 'title': title, 'text': text})


def get_contents(url):
    return json.loads(re.findall(
        r"Site\.page = (.+?)Site\.page\.template", requests.get(url).text, flags=re.DOTALL
    )[0].strip()[:-1])


def fix_links(text):
    return BeautifulSoup(
        re.sub(r"<a href=(.+?)>(.+?)</a>", r"[a href=\1]\2[/a]", str(text), flags=re.DOTALL), 'lxml'
    ).text


def get_thread_pattern(url):
    return '(' + url.replace('.', r'\.') + r'\?thread=\d+?#t\d+?)"'


if __name__ == '__main__':
    # scraper = NewStyle('https://formerchild.livejournal.com/39619.html', 'VV_formerchild.json')
    scraper = OldStyle('https://baaltii1.livejournal.com/198675.html')
    # scraper.scrape_post()
    scraper.launch()
    # scraper.scrape_pages()
    # scraper.scrape_comment('https://baaltii1.livejournal.com/198675.html?thread=1352723#t1352723')
    # scraper.scrape_comment('https://baaltii1.livejournal.com/198675.html?thread=1424147#t1424147')
    # scraper.scrape_comment('https://baaltii1.livejournal.com/198675.html?thread=1361171#t1361171')
