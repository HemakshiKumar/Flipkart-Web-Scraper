"""The scraper must keep using the selectors the notebook already had."""

from __future__ import annotations

from app.config import DEFAULT_SELECTORS
from app.services.scraper import FlipkartScraper

SEARCH_HTML = """
<html><body>
  <div><a class="wjcEIp" href="/product-one/p/itm123">One</a></div>
  <div><a class="wjcEIp" href="/product-two/p/itm456">Two</a></div>
  <div><a class="wjcEIp" href="/product-one/p/itm123">Duplicate</a></div>
  <div><a class="somethingElse" href="/ignored/p/itm789">Ignored</a></div>
</body></html>
"""

PRODUCT_HTML = """
<html><body>
  <span class="VU-ZEz">Aroma NB120 Amaze Neckband Bluetooth</span>
  <div class="Nx9bqj CxhGGd">&#8377;399</div>
  <div class="XQDdHH">4.1</div>
  <ul>
    <li class="_7eSDEz">With Mic:Yes</li>
    <li class="_7eSDEz">Battery life: 50 hr</li>
  </ul>
  <ul><li class="_1u+DIo">7 Days Replacement Policy?</li></ul>
  <span class="Wphh3N">1,234 Ratings &amp; 56 Reviews</span>
</body></html>
"""


def test_default_selectors_match_the_notebook() -> None:
    assert DEFAULT_SELECTORS["product_link"] == {"tag": "a", "class": "wjcEIp"}
    assert DEFAULT_SELECTORS["title"] == {"tag": "span", "class": "VU-ZEz"}
    assert DEFAULT_SELECTORS["price"] == {"tag": "div", "class": "Nx9bqj CxhGGd"}
    assert DEFAULT_SELECTORS["rating"] == {"tag": "div", "class": "XQDdHH"}
    assert DEFAULT_SELECTORS["details"] == {"tag": "li", "class": "_7eSDEz"}
    assert DEFAULT_SELECTORS["return_policy"] == {"tag": "li", "class": "_1u+DIo"}
    assert DEFAULT_SELECTORS["review_count"] == {"tag": "span", "class": "Wphh3N"}


def test_find_product_links_uses_anchor_class_and_dedupes() -> None:
    links = FlipkartScraper().find_product_links(SEARCH_HTML)
    assert links == [
        "https://www.flipkart.com/product-one/p/itm123",
        "https://www.flipkart.com/product-two/p/itm456",
    ]


def test_parse_product_extracts_every_notebook_field() -> None:
    product = FlipkartScraper().parse_product(PRODUCT_HTML, url="https://example.test/p")
    assert product.TITLE == "Aroma NB120 Amaze Neckband Bluetooth"
    assert product.PRICE == "₹399"
    assert product.AVG_RATING == "4.1"
    assert product.DETAILS == "With Mic:Yes; Battery life: 50 hr; "
    assert product.RETURN_POLICY == "7 Days Replacement Policy?; "
    assert product.REVIEW_COUNT == "1,234 Ratings & 56 Reviews"
    assert product.URL == "https://example.test/p"


def test_missing_fields_degrade_to_empty_strings() -> None:
    product = FlipkartScraper().parse_product("<html><body></body></html>")
    assert product.TITLE == ""
    assert product.DETAILS == ""


def test_search_url_is_query_encoded() -> None:
    url = FlipkartScraper().search_url("bluetooth headset")
    assert "q=bluetooth+headset" in url
