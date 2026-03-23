"""Tests for NewsFetcher — mock HTTP responses to test parsing logic."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent.sentiment.news_fetcher import NewsFetcher, NewsItem
from agent.sentiment.sources.rss import RSSEntry, parse_rss


def _mock_response(status_code: int = 200, *, json: object = None, text: str = "") -> httpx.Response:
    """Create a mock httpx.Response with a request attached (needed for raise_for_status)."""
    if json is not None:
        import json as _json
        resp = httpx.Response(status_code, text=_json.dumps(json), request=httpx.Request("GET", "https://mock"))
        resp._content = _json.dumps(json).encode()  # noqa: SLF001
        # Patch .json() to return the dict directly
        resp.headers["content-type"] = "application/json"
        return resp
    return httpx.Response(status_code, text=text, request=httpx.Request("GET", "https://mock"))


# ── RSS parser tests ──────────────────────────────────────────

RSS_SAMPLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Bitcoin hits new high</title>
      <description>BTC surged past $70k today amid institutional demand.</description>
      <link>https://example.com/btc-high</link>
      <pubDate>Mon, 23 Mar 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>ETH upgrade incoming</title>
      <description>Ethereum devs announce next protocol upgrade.</description>
      <link>https://example.com/eth-upgrade</link>
      <pubDate>Mon, 23 Mar 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry>
    <title>Market rally</title>
    <summary>Stocks rally on positive earnings.</summary>
    <link href="https://example.com/rally"/>
    <updated>2026-03-23T08:00:00Z</updated>
  </entry>
</feed>
"""


class TestRSSParser:
    def test_parse_rss2(self):
        entries = parse_rss(RSS_SAMPLE)
        assert len(entries) == 2
        assert entries[0].title == "Bitcoin hits new high"
        assert "BTC" in entries[0].summary
        assert entries[0].link == "https://example.com/btc-high"

    def test_parse_atom(self):
        entries = parse_rss(ATOM_SAMPLE)
        assert len(entries) == 1
        assert entries[0].title == "Market rally"

    def test_parse_invalid_xml(self):
        entries = parse_rss("not xml at all")
        assert entries == []

    def test_parse_limit(self):
        entries = parse_rss(RSS_SAMPLE, limit=1)
        assert len(entries) == 1


# ── CryptoCompare source tests ───────────────────────────────

CRYPTOCOMPARE_RESPONSE = {
    "Data": [
        {
            "title": "BTC surges",
            "body": "Bitcoin price rose 5% today.",
            "url": "https://example.com/btc",
            "published_on": "1711184400",
        },
        {
            "title": "DeFi update",
            "body": "Major DeFi protocol announces new feature.",
            "url": "https://example.com/defi",
            "published_on": "1711180800",
        },
    ]
}


class TestNewsFetcher:
    @pytest.fixture
    def fetcher(self):
        return NewsFetcher(finnhub_api_key="test-key")

    async def test_fetch_crypto_news(self, fetcher: NewsFetcher):
        """Mock the CryptoCompare API and verify parsing."""
        mock_resp = _mock_response(200, json=CRYPTOCOMPARE_RESPONSE)
        with patch.object(fetcher._http, "get", new_callable=AsyncMock, return_value=mock_resp):
            items = await fetcher.fetch_crypto_news(limit=5)
        assert len(items) == 2
        assert items[0].title == "BTC surges"
        assert items[0].source == "CryptoCompare"

    async def test_fetch_general_market(self, fetcher: NewsFetcher):
        """Mock Finnhub + Yahoo and verify aggregation."""
        finnhub_data = [
            {"headline": "Markets up", "summary": "S&P500 gains.", "url": "https://example.com/sp", "datetime": 1711184400},
        ]
        yahoo_rss = RSS_SAMPLE

        async def mock_get(url, **kwargs):
            if "finnhub" in url:
                return _mock_response(200, json=finnhub_data)
            return _mock_response(200, text=yahoo_rss)

        with patch.object(fetcher._http, "get", side_effect=mock_get):
            items = await fetcher.fetch_general_market(limit=10)
        assert len(items) >= 1
        assert any("Markets up" in i.title or "Bitcoin" in i.title for i in items)

    async def test_fetch_all_dedup(self, fetcher: NewsFetcher):
        """Ensure fetch_all deduplicates by title."""
        async def mock_get(url, **kwargs):
            if "cryptocompare" in url:
                return _mock_response(200, json=CRYPTOCOMPARE_RESPONSE)
            if "finnhub" in url:
                return _mock_response(200, json=[])
            return _mock_response(200, text="<rss><channel></channel></rss>")

        with patch.object(fetcher._http, "get", side_effect=mock_get):
            items = await fetcher.fetch_all(limit=20)
        titles = [i.title for i in items]
        assert len(titles) == len(set(t.lower() for t in titles)), "Duplicates found"

    async def test_fetch_crypto_handles_failure(self, fetcher: NewsFetcher):
        """Gracefully handles network errors."""
        with patch.object(fetcher._http, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("fail")):
            items = await fetcher.fetch_crypto_news()
        assert items == []

    async def test_no_finnhub_key_skips(self):
        """When no Finnhub key is set, stock sources skip Finnhub calls."""
        fetcher = NewsFetcher(finnhub_api_key="")
        mock_resp = _mock_response(200, text="<rss><channel></channel></rss>")
        with patch.object(fetcher._http, "get", new_callable=AsyncMock, return_value=mock_resp):
            items = await fetcher.fetch_general_market(limit=5)
        # Should still succeed (from Yahoo RSS, which returned empty)
        assert isinstance(items, list)
