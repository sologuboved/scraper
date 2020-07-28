def scrape_thread_urls(self, page_url):
    print("Scraping thread URLs from {}...".format(page_url))
    contents = get_contents(page_url)
    self.thread_urls |= {comment['thread_url'] for comment in contents['comments']}
    print("Currently {} thread urls".format(len(self.thread_urls)))
