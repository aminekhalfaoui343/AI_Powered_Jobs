"""Text cleaning helpers shared by scrapers."""

from bs4 import BeautifulSoup, Tag


def clean_text(text: str) -> str:
    """Collapse whitespace and strip each line."""
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


def element_text(element: Tag | None) -> str | None:
    """Return cleaned text from a BeautifulSoup element, or None."""
    if element is None:
        return None
    text = element.get_text(separator="\n", strip=True)
    return text if text else None


def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def remove_noise(soup: BeautifulSoup) -> None:
    """Remove scripts, styles, and navigation chrome in-place."""
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()


def build_raw_text(soup: BeautifulSoup, main_selector: str | None = None) -> str:
    """
    Build readable plain text from a page.

    If main_selector is provided, focus on that container first.
    Falls back to the whole page body.
    """
    remove_noise(soup)

    if main_selector:
        main = soup.select_one(main_selector)
        if main:
            return clean_text(main.get_text(separator="\n", strip=True))

    body = soup.body or soup
    return clean_text(body.get_text(separator="\n", strip=True))
