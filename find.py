import datetime
import feedgen.feed
import html
import json
import os
import re
import requests
import urllib.parse

from xml.etree import ElementTree


def main():
    url = "https://downloadlibrary.overdrive.com/collection/1067423?addedDate=days-0-7&language=en&maturityLevel=generalcontent&maturityLevel=youngadult"

    page = DownloadLibraryCataloguePage(url)
    books = load_books_from_starting_page(page)

    if not books:
        print("No new books at library.")
        return

    feed_generator = feedgen.feed.FeedGenerator()
    feed_generator.id("https://blairconrad.com/new-ebooks-at-downloadlibrary")
    feed_generator.title("Blair's list of new e-books at downloadLibrary")
    feed_generator.author(name="Blair Conrad", email="blair@blairconrad.com")

    recover_feed_entries_from_file(feed_generator, "atom.xml")

    for entry in feed_generator.entry():
        books.pop(entry.id(), None)

    if not books:
        print("All new books have been seen already.")
        return

    books = sorted(books.values(), key=lambda b: b.creator_name)
    add_books_to_feed(feed_generator, books)
    feed_generator.atom_file("atom.xml", pretty=True)


def recover_feed_entries_from_file(feed_generator, feed_path):
    ns = "{http://www.w3.org/2005/Atom}"
    if not os.path.isfile(feed_path):
        return
    root = ElementTree.parse(feed_path).getroot()
    for entry in root.iter(f"{ns}entry"):
        recovered_entry = feed_generator.add_entry(order="append")
        recovered_entry.id(entry.find(f"{ns}id").text)
        recovered_entry.title(entry.find(f"{ns}title").text)
        recovered_entry.link(href=entry.find(f"{ns}link").attrib["href"])
        recovered_entry.content(type="html", content=entry.find(f"{ns}content").text)
        recovered_entry.published(entry.find(f"{ns}published").text)
        recovered_entry.updated(entry.find(f"{ns}updated").text)


def add_books_to_feed(feed_generator, books):
    now = datetime.datetime.now(datetime.timezone.utc)

    for ebook in books:
        entry = feed_generator.add_entry()
        entry.id(ebook.id)
        entry.title(
            ebook.title + " by " + ebook.creator_name + " is in the downloadLibrary"
        )
        subtitle = ebook.subtitle and f"<h3>{ebook.subtitle}</h3>" or ""
        content = f"""
<a href="{ebook.get_url()}">
<img src="{ebook.cover_url}">
<h2>{ebook.title}</h2>
{subtitle}
</a>
is an ebook and is available at the downloadLibrary.
<p>Subjects: {ebook.subjects}</p>
<blockquote>
{ebook.description}
</blockquote>
"""
        entry.link(href=ebook.get_url())
        entry.content(type="html", content=content)
        entry.published(now)
        entry.updated(now)


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
    def __init__(
        self, id, title, subtitle, creator_name, cover_url, description, subjects
    ):
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.creator_name = creator_name
        self.cover_url = cover_url
        self.description = description
        self.subjects = subjects

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
            subtitle=dict.get("subtitle", None),
            creator_name=dict["firstCreatorName"],
            cover_url=dict["covers"]["cover150Wide"]["href"],
            description=dict["description"],
            subjects=", ".join(sorted([s["name"] for s in dict["subjects"]])),
        )


if __name__ == "__main__":
    main()
