import os
import re
import time
import requests
from bs4 import BeautifulSoup
from helpers import dump_utf_json, load_utf_json, which_watch
from userinfo import MY_BLOG_URL

_headers = {'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/41.0.2272.101 "
                          "Safari/537.36"}


class BooklistScraper:
    def __init__(self, url, target):
        self.url = url
        self.target_raw = target + '.json'
        self.target_html = target + '.txt'
        self.books = list()

    @which_watch
    def launch(self):
        self.scroll_pages()
        self.books.sort(key=lambda b: b[0].split()[-1])
        print("Dumping {}...".format(self.target_raw))
        dump_utf_json(self.books, self.target_raw)
        convert_to_html(self.target_html, src_json=self.target_raw)

    def scroll_pages(self):
        while self.url:
            print("Scraping {}...".format(self.url))
            soup = BeautifulSoup(requests.get(self.url, headers=_headers).content, 'lxml')
            try:
                self.url = self.get_full_url(soup.find('a', {'rel': 'next'}).get('href'))
            except AttributeError:
                self.url = None
            self.download_page(soup)

    def download_page(self, soup):
        for a in soup.find_all('td'):
            try:
                author_name = a.find('a', {'class': 'authorName'}).text.strip()
            except AttributeError:
                continue
            raw_title = a.find('a', {'class': 'bookTitle'})
            book_url = self.get_full_url(raw_title.get('href').strip())
            soup = BeautifulSoup(requests.get(book_url, headers=_headers).content, 'lxml')
            self.books.append([author_name, book_url, raw_title.text.strip(), get_first_publication_year(soup)])
        print("Currently {} books...".format(len(self.books)))

    @staticmethod
    def get_full_url(url):
        return 'https://www.goodreads.com' + url


@which_watch
def add_books(src_entry_url, booklist_json, links_src_txt, target_html, target_json):
    print(f"Adding books from {links_src_txt} to {target_html}...")
    assert src_entry_url or booklist_json, "Neither source entry URL nor source .json provided"
    if not src_entry_url:
        booklist = load_utf_json(booklist_json)
    else:
        booklist = scrape_booklist_from_blog(src_entry_url, target_json)
    print(f"{len(booklist)} books so far")
    additional_books = scrape_booklist_from_file(links_src_txt)
    print(f"Got {len(additional_books)} additional books")
    additional_books = clean_out_duplicates(additional_books, booklist)
    booklist.extend(additional_books)
    print(f"{len(booklist)} currently")
    sort_booklist(booklist)
    if target_json:
        dump_utf_json(booklist, target_json)
    convert_to_html(target_html, booklist)


def scrape_booklist_from_blog(entry_url, target_json):
    entry_url = MY_BLOG_URL.format(entry_url)
    print(f"Scraping from {entry_url} to {target_json}...")
    booklist = list()
    pattern = re.compile(r'<li>(.+?) – <a href="(.+?)">(.+?)</a> \((\d{4}|\?)\)</li>')
    for line in BeautifulSoup(
        requests.get(entry_url, headers=_headers).content, 'lxml'
    ).find('div', {'class': 'entry-content'}).find('ol').find_all('li'):
        booklist.append(pattern.findall(str(line))[0])
    if target_json:
        sort_booklist(booklist)
        dump_utf_json(booklist, target_json)
    return booklist


def sort_booklist(booklist):
    def sorter(book):
        first_author = book[0].split(',')[0].strip().split()
        try:
            is_jr = first_author[-1].strip().lower().startswith('jr')
        except IndexError:
            print(book)
            raise
        if is_jr:
            return first_author[-2]
        else:
            return first_author[-1]

    print(f"Sorting booklist...")
    booklist.sort(key=sorter)
    return booklist


def scrape_booklist_from_file(links_src_txt):
    print(f"Scraping books from {links_src_txt}...")
    booklist = list()
    with open(links_src_txt, 'rt') as handler:
        book_urls = list(map(str.strip, handler.readlines()))
    total = len(book_urls)
    count = 0
    for book_url in book_urls:
        count += 1
        print(f"({count} / {total})", end=" ")
        booklist.append(scrape_book(book_url))
    return booklist


def scrape_book(book_url):
    print(book_url)
    time.sleep(2)
    attempts = 10
    while attempts:
        soup = BeautifulSoup(requests.get(book_url, headers=_headers).content, 'lxml')
        try:
            return [
                get_author_name(soup),
                book_url,
                get_book_title(soup),
                get_first_publication_year(soup)
            ]
        except AttributeError:
            attempts -= 1
            print(f"...{attempts} attempts remain")
            time.sleep(5)


def get_author_name(soup):
    author_name = ", ".join([author_name.text.strip() for author_name in soup.find_all('a', {'class': 'authorName'})])
    if not author_name:
        author_name = soup.find('title').text.split('by')[-1].rsplit('|', 1)[0].strip()
    return author_name


def get_book_title(soup):
    try:
        return soup.find('h1', {'id': 'bookTitle'}).text.strip()
    except AttributeError:
        return soup.find('meta', {'property': 'og:title'}).get('content')


def get_first_publication_year(soup):
    year = None
    try:
        year = soup.find('nobr', {'class': 'greyText'}).text.strip()
    except AttributeError:
        try:
            details = soup.find_all('div', {'id': 'details'})[0].find_all('div', {'class': 'row'})
        except IndexError:
            pass
        else:
            for row in details:
                try:
                    year = re.findall(r"Published.+?(\d\d\d\d)", row.text, flags=re.DOTALL)[0]
                except IndexError:
                    continue
                break
    else:
        year = re.findall(r'\d\d\d\d', year)[0]
    if not year:
        year = '?'
    return year


def clean_out_duplicates(raw_booklist, booklist):
    print("Cleaning out duplicates...")
    clean_booklist = list()
    book_urls = {book[1] for book in booklist}
    for book in raw_booklist:
        if book[1] in book_urls:
            print("Already in booklist:", book)
        else:
            clean_booklist.append(book)
    print(f"{len(clean_booklist)} books remain")
    return clean_booklist


def convert_to_html(target_html, src_booklist=None, src_json=None):
    print(f"Converting to {target_html}...")
    assert src_booklist or src_json, "Neither source booklist nor source .json provided"
    if src_json:
        src_booklist = load_utf_json(src_json)
    with open(target_html, 'wt') as handler:
        handler.write('<ol>\n')
        for author_name, book_url, title, year in src_booklist:
            handler.write('<li>{} - <a href="{}">{}</a> ({})</li>\n'.format(author_name, book_url, title, year))
        handler.write('</ol>')


if __name__ == '__main__':
    add_books(
        '2020/07/26/non-fiction-on-conspiracy-theories/',
        None,
        os.path.join('data', 'gr_booklist_conspir_src.txt'),
        os.path.join('data', 'gr_booklist_conspir.html'),
        os.path.join('data', 'gr_booklist_conspir.json'))
    add_books(
        '2020/07/31/non-fiction-on-extraterrestrial-life/',
        None,
        os.path.join('data', 'gr_booklist_extraterr_src.txt'),
        os.path.join('data', 'gr_booklist_extraterr.html'),
        os.path.join('data', 'gr_booklist_extraterr.json'))
