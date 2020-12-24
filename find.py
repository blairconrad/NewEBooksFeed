import datetime
import html
import json
import re
import requests
import urllib.parse

from feedgen.feed import FeedGenerator


def main():
    url = "https://downloadlibrary.overdrive.com/collection/1067423?addedDate=days-0-7&language=en&maturityLevel=generalcontent&maturityLevel=youngadult"

    page = DownloadLibraryCataloguePage(url)
    books = load_books_from_starting_page(page).values()
    books = sorted(books, key=lambda b: b.creator_name)

    for book in books:
        print(f"{book.creator_name}\t{book.title}")

    create_feed(books)


def create_feed(books):
    now = datetime.datetime.now(datetime.timezone.utc)
    generator = FeedGenerator()

    generator.id("https://blairconrad.com/new-ebooks-at-downloadlibrary")
    generator.title("Blair's list of new e-books at downloadLibrary")
    generator.author(name="Blair Conrad", email="blair@blairconrad.com")

    for ebook in books:
        entry = generator.add_entry(order="append")
        entry.id(ebook.id)
        entry.title(
            ebook.title + " by " + ebook.creator_name + " is in the downloadLibrary"
        )
        content = f"""
<a href="{ebook.get_url()}">
<img src="{ebook.cover_url}">
<h2>{ebook.title}</h2>
</a>
is an ebook and is available at the downloadLibrary.
"""
        entry.link(href=ebook.get_url())
        entry.content(type="html", content=content)
        entry.published(now)
        entry.updated(now)

    generator.atom_file("atom.xml", pretty=True)  # Write the ATOM feed to a file


def load_books_from_starting_page(page):
    books = {}

    while True:
        page.fetch_books()
        if page.books:
            books.update(page.books)
        if not page.next_page_url:
            break
        page = DownloadLibraryCataloguePage(page.next_page_url)
    return books


class Book:
    def __init__(self, id, title, creator_name, cover_url):
        self.id = id
        self.title = title
        self.creator_name = creator_name
        self.cover_url = cover_url

    def get_url(self):
        return "https://downloadlibrary.overdrive.com/media/" + self.id


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
            json_text = match.group(1)
            dict_books = json.loads(json_text)
            self.books = {
                key: self._make_book_from_dictionary(value)
                for (key, value) in dict_books.items()
            }

    def _make_book_from_dictionary(self, dict):
        return Book(
            id=dict["id"],
            title=dict["title"],
            creator_name=dict["firstCreatorName"],
            cover_url=dict["covers"]["cover150Wide"]["href"],
        )


if __name__ == "__main__":
    main()