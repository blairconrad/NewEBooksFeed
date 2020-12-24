import html
import json
import re
import requests
import urllib.parse

from feedgen.feed import FeedGenerator
from xml.etree import ElementTree


def main():
    url = "https://downloadlibrary.overdrive.com/collection/1067423?addedDate=days-0-7&language=en&maturityLevel=generalcontent&maturityLevel=youngadult"

    page = DownloadLibraryCataloguePage(url)
    page.fetch_books()

    while page.next_page_url:
        if page.books:
            for book in page.books.values():
                print(book["title"])
        page = DownloadLibraryCataloguePage(page.next_page_url)
        page.fetch_books()


class DownloadLibraryCataloguePage:
    def __init__(self, url):
        self.url = url
        self.books = {}
        self.next_page_url = None

    def fetch_books(self):
        fetch_response = requests.get(self.url)
        print(f"fetching {self.url}")
        response_text = fetch_response.text
        self._load_books_from_response(response_text)
        self._load_next_page_url_from_response(response_text)

    def _load_next_page_url_from_response(self, response_text):
        match = re.search('Next page.*href="([^"]*days-0-7[^"]*)', response_text)
        if match:
            next_page_url = html.unescape(match.group(1))
            self.next_page_url = urllib.parse.urljoin(self.url, next_page_url)

    def _load_books_from_response(self, response_text):
        match = re.search(
            r"window\.OverDrive\.mediaItems\s*=\s*([^\n]+);",
            response_text,
        )
        if match:
            json_books = match.group(1)
            self.books = json.loads(json_books)


if __name__ == "__main__":
    main()