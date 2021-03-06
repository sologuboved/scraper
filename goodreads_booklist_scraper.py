import re
import requests
from bs4 import BeautifulSoup
from helpers import dump_utf_json, load_utf_json, which_watch


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
        convert_to_html(self.target_raw, self.target_html)

    def scroll_pages(self):
        while self.url:
            print("Scraping {}...".format(self.url))
            soup = BeautifulSoup(requests.get(self.url).content, 'lxml')
            try:
                self.url = get_full_url(soup.find('a', {'rel': 'next'}).get('href'))
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
            book_url = get_full_url(raw_title.get('href').strip())
            soup = BeautifulSoup(requests.get(book_url).content, 'lxml')
            self.books.append([author_name, book_url, raw_title.text.strip(), get_first_publication_year(soup)])
        print("Currently {} books...".format(len(self.books)))


def convert_to_html(target_raw, target_html):
    print("{} -> {}...".format(target_raw, target_html))
    with open(target_html, 'wt') as handler:
        handler.write('<ol>\n')
        for author_name, book_url, title, year in load_utf_json(target_raw):
            handler.write('<li>{} - <a href="{}">{}</a> ({})</li>\n'.format(author_name, book_url, title, year))
        handler.write('</ol>')


def get_full_url(url):
    return 'https://www.goodreads.com' + url


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
    return year


def scrape_booklist_from_file(target, src_txt='data/booklist_src.txt'):
    target_raw = target + '.json'
    target_html = target + '.txt'
    print(f"Comprising {target_raw} & {target_html} from {src_txt}...")
    with open(src_txt, 'rt') as handler:
        book_urls = list(map(str.strip, handler.readlines()))
    books = [scrape_book(book_url) for book_url in book_urls]
    dump_utf_json(books, target_raw)
    convert_to_html(target_raw, target_html)


def scrape_book(book_url):
    print(book_url)
    soup = BeautifulSoup(requests.get(book_url).content, 'lxml')
    return [
        ", ".join([author_name.text.strip() for author_name in soup.find_all('a', {'class': 'authorName'})]),
        book_url,
        soup.find('h1', {'id': 'bookTitle'}).text.strip(),
        get_first_publication_year(soup)
    ]


if __name__ == '__main__':
    # scraper = BooklistScraper('https://www.goodreads.com/list/show/151185.Non_Fiction_on_Extraterrestial_Life',
    #                           'gr_booklist_extraterr')
    # scraper.launch()
    scrape_booklist_from_file('data/booklist')
    # print(scrape_book('https://www.goodreads.com/book/show/1873604.Theories_of_Mimesis'))
