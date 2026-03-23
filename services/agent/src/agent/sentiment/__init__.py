"""News sentiment analysis module for the Kainex AI Trading Agent."""

from agent.sentiment.analyzer import SentimentAnalyzer, SentimentResult
from agent.sentiment.news_fetcher import NewsFetcher, NewsItem

__all__ = ["NewsFetcher", "NewsItem", "SentimentAnalyzer", "SentimentResult"]
