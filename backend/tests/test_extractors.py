"""The structural fallback must never override a working configured selector."""

from __future__ import annotations

import json

from app.config import get_settings
from app.services import extractors
from app.services.scraper import FlipkartScraper

PRODUCT_JSON_LD = {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Noise Airwave Max 2, 50H Battery, 40mm Driver Bluetooth",
    "description": (
        "Buy Noise Airwave Max 2 for Rs.2999.0 Online. 50 hours of playback. "
        "Deep bass drivers; Dual pairing; Only Genuine Products. Free Shipping."
    ),
    "offers": {"price": 1499, "priceCurrency": "INR"},
}

SEARCH_PAGE = """
<html><body>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"ItemList","itemListElement":[
  {"@type":"ListItem","position":1,"url":"https://www.flipkart.com/a/p/itm111"},
  {"@type":"ListItem","position":2,"url":"https://www.flipkart.com/b/p/itm222"}]}
</script>
<a class="someGeneratedClass" href="/c/p/itm333">Third</a>
</body></html>
"""

MODERN_PRODUCT_PAGE = """
<html><body>
  <h1>Noise Airwave Max 2, 50H Battery ... more</h1>
  <div class="css-g5y9jx">&#8377;1,499</div>
  <script type="application/ld+json">%s</script>
  <script>window.__STATE__={"pr":{"rating":4.4,"ratingsCount":3013,"reviewsCount":217}}</script>
</body></html>
""" % json.dumps(PRODUCT_JSON_LD)

LEGACY_PRODUCT_PAGE = """
<html><body>
  <span class="VU-ZEz">Legacy Title</span>
  <div class="Nx9bqj CxhGGd">&#8377;999</div>
  <div class="XQDdHH">4.1</div>
  <li class="_7eSDEz">Battery life: 50 hr</li>
  <span class="Wphh3N">10 Ratings &amp; 2 Reviews</span>
  <script type="application/ld+json">%s</script>
</body></html>
""" % json.dumps(PRODUCT_JSON_LD)


def test_links_come_from_the_json_ld_item_list() -> None:
    links = extractors.extract_product_links(SEARCH_PAGE, "https://www.flipkart.com")
    assert links == [
        "https://www.flipkart.com/a/p/itm111",
        "https://www.flipkart.com/b/p/itm222",
    ]


def test_links_fall_back_to_the_product_url_shape() -> None:
    html = '<a class="x" href="/c/p/itm333">Third</a><a href="/d/p/itm444">Fourth</a>'
    links = extractors.extract_product_links(html, "https://www.flipkart.com")
    assert links == [
        "https://www.flipkart.com/c/p/itm333",
        "https://www.flipkart.com/d/p/itm444",
    ]


def test_modern_page_is_parsed_when_the_notebook_selectors_miss() -> None:
    product = FlipkartScraper().parse_product(MODERN_PRODUCT_PAGE, url="https://x.test/p")

    assert product.TITLE == "Noise Airwave Max 2, 50H Battery, 40mm Driver Bluetooth"
    assert product.PRICE == "₹1,499"
    assert product.AVG_RATING == "4.4"
    assert product.REVIEW_COUNT == "3,013 Ratings & 217 Reviews"
    assert "playback" in product.DETAILS
    # Storefront boilerplate is dropped from the TF-IDF corpus.
    assert "Genuine Products" not in product.DETAILS
    assert "Free Shipping" not in product.DETAILS


def test_configured_selectors_win_over_the_fallback() -> None:
    product = FlipkartScraper().parse_product(LEGACY_PRODUCT_PAGE)

    assert product.TITLE == "Legacy Title"
    assert product.PRICE == "₹999"
    assert product.AVG_RATING == "4.1"
    assert product.REVIEW_COUNT == "10 Ratings & 2 Reviews"
    assert product.DETAILS == "Battery life: 50 hr; "


def test_fallback_can_be_disabled() -> None:
    settings = get_settings().model_copy(update={"structural_fallback": False})
    product = FlipkartScraper(settings).parse_product(MODERN_PRODUCT_PAGE)
    assert product.TITLE == ""
    assert product.PRICE == ""


def test_zero_ratings_are_reported_as_missing_not_as_zero_stars() -> None:
    html = '<script>{"pr":{"rating":0,"ratingsCount":0,"reviewsCount":0}}</script>'
    assert extractors.extract_rating(html) == ""
    assert extractors.extract_review_count(html) == ""
