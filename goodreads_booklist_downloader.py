import re
import requests
from bs4 import BeautifulSoup
from helpers import dump_utf_json, load_utf_json, which_watch, counter


def download_raw_booklist(url, num_pages, target_json):
    books = list()
    for page_num in range(1, num_pages + 1):
        for a in BeautifulSoup(requests.get(url.format(page_num)).content, 'lxml').find_all('td'):
            try:
                author_name = a.find('a', {'class': 'authorName'}).text.strip()
            except AttributeError:
                continue
            raw_title = a.find('a', {'class': 'bookTitle'})
            books.append([author_name, raw_title.text.strip(), raw_title.get('href').strip()])
    books.sort(key=lambda b: b[0].split()[-1])
    print("Dumping {} books...".format(len(books)))
    dump_utf_json(books, target_json)


def process_booklist(src_json, target_txt):
    with open(target_txt, 'wt') as handler:
        handler.write('<ol>')
        for author_name, title, title_url, year in load_utf_json(src_json):
            handler.write('<li>{} - <a href="{}">{}</a> ({})</li>'.format(author_name, get_full_url(title_url),
                                                                          title, year))
        handler.write('</ol>')


def get_full_url(url):
    return 'https://www.goodreads.com' + url


@which_watch
def add_first_publication_years(src_json):
    books = load_utf_json(src_json)
    count = counter(len(books))
    for book in books:
        next(count)
        book.append(get_first_publication_year(book[-1]))
    print("\nDumping {} yeared books...".format(len(books)))
    dump_utf_json(books, src_json)


def get_first_publication_year(book_url):
    book_url = get_full_url(book_url)
    soup = BeautifulSoup(requests.get(book_url).content, 'lxml')
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


if __name__ == '__main__':
    json_fname = 'gr_raw_booklist_extraterr.json'
    download_raw_booklist('https://www.goodreads.com/list/show/151185.Non_Fiction_on_Extraterrestial_Life?page={}',
                          1, json_fname)
    add_first_publication_years(json_fname)
    process_booklist(json_fname, 'gr_booklist_extraterr.txt')
