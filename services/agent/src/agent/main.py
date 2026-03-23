from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone

from agent.config import AgentSettings
from agent.executor import TradeExecutor
from agent.feedback import FeedbackAnalyzer
from agent.llm import LLMClient
from agent.market_analyzer import MarketAnalyzer
from agent.prompt_builder import PromptBuilder
from agent.sentiment import NewsFetcher, SentimentAnalyzer, SentimentResult
from agent.strategy_journal import StrategyJournal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent")

# Minimum cycles before considering a strategy iteration.
MIN_ITERATION_CYCLES = 6


def _current_parameters(settings: AgentSettings) -> dict:
    """Snapshot the strategy-relevant settings into a plain dict."""
    return {
        "persona": settings.persona,
        "stop_loss_pct": settings.stop_loss_pct,
        "max_position_pct": settings.max_position_pct,
        "initial_capital": settings.initial_capital,
        "symbols": list(settings.symbols),
        "trading_interval_minutes": settings.trading_interval_minutes,
    }


async def run_cycle(
    settings: AgentSettings,
    llm: LLMClient,
    analyzer: MarketAnalyzer,
    builder: PromptBuilder,
    executor: TradeExecutor,
    feedback: FeedbackAnalyzer,
    journal: StrategyJournal,
    news_fetcher: NewsFetcher,
    sentiment_analyzer: SentimentAnalyzer,
    version_id: str,
    cycle: int,
) -> str:
    """Execute a single analysis-trade cycle for all configured symbols.

    Returns the (possibly new) active *version_id*.
    """
    logger.info("=== Cycle %d started (strategy %s) ===", cycle, version_id)

    # Fetch news and run sentiment analysis before market decisions.
    sentiment: SentimentResult | None = None
    try:
        news_items = await news_fetcher.fetch_all(symbols=list(settings.symbols), limit=15)
        logger.info("Fetched %d news items", len(news_items))
        if news_items:
            sentiment = await sentiment_analyzer.analyze(news_items)
            logger.info(
                "Sentiment: %s (confidence=%.2f) — %s",
                sentiment.overall_sentiment,
                sentiment.confidence,
                sentiment.summary,
            )
            journal.record_sentiment(version_id, sentiment)
    except Exception:
        logger.exception("News/sentiment analysis failed, continuing without sentiment")

    portfolio = await analyzer.get_portfolio_state()

    risk_constraints = {
        "max_position_pct": settings.max_position_pct,
        "stop_loss_pct": settings.stop_loss_pct,
        "initial_capital": settings.initial_capital,
    }

    # Build performance context for the prompt.
    perf_summary = journal.get_performance_summary(version_id)

    # Retrieve the previous version's iteration suggestion (if any).
    active = journal.get_active_version()
    iteration_suggestion = active.get("reasoning", "") if active else ""

    for symbol in settings.symbols:
        logger.info("Analyzing %s ...", symbol)

        # 1. Get market state
        market_summary = await analyzer.get_market_summary(symbol)

        # 2. Build prompt (now with historical context + sentiment)
        prompt = builder.build(
            persona=settings.persona,
            market_summary=market_summary,
            portfolio=portfolio,
            risk_constraints=risk_constraints,
            performance_summary=perf_summary,
            iteration_suggestion=iteration_suggestion,
            sentiment=sentiment,
        )

        # 3. LLM decision
        decision = await llm.analyze(prompt)
        logger.info(
            "LLM sentiment for %s: %s",
            symbol,
            decision.get("overall_sentiment", "?"),
        )
        if decision.get("analysis"):
            logger.info("Analysis: %s", decision["analysis"][:200])

        # 4. Record each sub-decision to journal and execute
        for d in decision.get("decisions", []):
            action = d.get("action", "hold")
            confidence = d.get("confidence", 0.0)
            dec_symbol = d.get("symbol", symbol)

            # Record the decision (including holds).
            journal.record_decision(version_id, {
                "cycle": cycle,
                "symbol": dec_symbol,
                "action": action,
                "confidence": confidence,
                "analysis": decision.get("analysis", ""),
                "raw_response": json.dumps(decision, ensure_ascii=False),
            })

            if action == "hold":
                logger.info("Hold %s (confidence=%.2f)", dec_symbol, confidence)
                continue

            result = await executor.execute(d)
            logger.info(
                "Execution result for %s %s: %s",
                action,
                dec_symbol,
                result.get("status"),
            )

            # Record the trade.
            journal.record_trade(version_id, {
                "symbol": dec_symbol,
                "action": action,
                "price": d.get("stop_loss", 0.0),  # placeholder; real price from executor
                "quantity": d.get("quantity", 0.0),
                "reason": d.get("reason", ""),
                "confidence": confidence,
                "pnl": None,  # unknown until position closes
            })

    # 5. Strategy iteration check (every MIN_ITERATION_CYCLES cycles)
    if cycle > 0 and cycle % MIN_ITERATION_CYCLES == 0:
        version_id = await _maybe_iterate_strategy(
            settings, llm, builder, journal, version_id, cycle
        )

    logger.info("=== Cycle %d completed ===", cycle)
    return version_id


async def _maybe_iterate_strategy(
    settings: AgentSettings,
    llm: LLMClient,
    builder: PromptBuilder,
    journal: StrategyJournal,
    version_id: str,
    cycle: int,
) -> str:
    """Ask the LLM whether the current strategy should be iterated.

    If yes, create a new version and return the new version_id; otherwise
    return the existing one.
    """
    logger.info("Running strategy iteration review (cycle %d) ...", cycle)

    perf_summary = journal.get_performance_summary(version_id)
    params = _current_parameters(settings)

    prompt = builder.build_iteration_prompt(
        version_id=version_id,
        performance_summary=perf_summary,
        cycle_count=cycle,
        current_parameters=params,
    )

    result = await llm.analyze(prompt)

    should_iterate = result.get("should_iterate", False)
    reason = result.get("iteration_reason", "")
    analysis = result.get("analysis", "")

    logger.info("Iteration review: should_iterate=%s, reason=%s", should_iterate, reason[:200])

    if not should_iterate:
        return version_id

    # Apply new parameters to settings with hard validation limits.
    _ALLOWED_PERSONAS = {"conservative", "balanced", "aggressive"}
    new_params = result.get("new_parameters", {})

    if "persona" in new_params:
        val = new_params["persona"]
        if val in _ALLOWED_PERSONAS:
            logger.info("Parameter change: persona %s -> %s", settings.persona, val)
            settings.persona = val
        else:
            logger.warning("LLM suggested invalid persona '%s', ignoring", val)

    if "stop_loss_pct" in new_params:
        val = float(new_params["stop_loss_pct"])
        val = max(0.01, min(0.15, val))
        logger.info("Parameter change: stop_loss_pct %s -> %s", settings.stop_loss_pct, val)
        settings.stop_loss_pct = val

    if "max_position_pct" in new_params:
        val = float(new_params["max_position_pct"])
        val = max(0.1, min(0.9, val))
        logger.info("Parameter change: max_position_pct %s -> %s", settings.max_position_pct, val)
        settings.max_position_pct = val

    # Create new strategy version.
    merged_params = _current_parameters(settings)
    new_version_id = journal.create_version(
        persona=settings.persona,
        model=settings.model,
        parameters=merged_params,
        reasoning=f"{analysis}\n\n调整原因: {reason}",
    )

    logger.info("Strategy iterated: %s -> %s", version_id, new_version_id)
    return new_version_id


async def run() -> None:
    settings = AgentSettings()

    # Validate API key.
    if not settings.openrouter_api_key:
        logger.error(
            "KAINEX_AGENT_OPENROUTER_API_KEY is not set. "
            "Please set this environment variable to your OpenRouter API key."
        )
        sys.exit(1)

    logger.info("Starting Kainex AI Trading Agent")
    logger.info("  Model:    %s", settings.model)
    logger.info("  Persona:  %s", settings.persona)
    logger.info("  Symbols:  %s", ", ".join(settings.symbols))
    logger.info("  Interval: %d minutes", settings.trading_interval_minutes)

    llm = LLMClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=settings.model,
    )
    analyzer = MarketAnalyzer(
        duckdb_path=settings.duckdb_path,
        engine_api_url=settings.engine_api_url,
    )
    builder = PromptBuilder()
    executor = TradeExecutor(settings.engine_api_url)
    feedback_analyzer = FeedbackAnalyzer()
    journal = StrategyJournal()
    news_fetcher = NewsFetcher(finnhub_api_key=settings.finnhub_api_key)
    sentiment_analyzer = SentimentAnalyzer(llm_client=llm)

    # Create initial strategy version.
    version_id = journal.create_version(
        persona=settings.persona,
        model=settings.model,
        parameters=_current_parameters(settings),
        reasoning="初始策略版本",
    )
    logger.info("Active strategy version: %s", version_id)

    cycle = 0
    try:
        while True:
            try:
                version_id = await run_cycle(
                    settings,
                    llm,
                    analyzer,
                    builder,
                    executor,
                    feedback_analyzer,
                    journal,
                    news_fetcher,
                    sentiment_analyzer,
                    version_id,
                    cycle,
                )
            except Exception:
                logger.exception("Error in cycle %d", cycle)

            cycle += 1
            logger.info(
                "Sleeping %d minutes until next cycle ...",
                settings.trading_interval_minutes,
            )
            await asyncio.sleep(settings.trading_interval_minutes * 60)
    except asyncio.CancelledError:
        logger.info("Agent cancelled")
    finally:
        await analyzer.close()
        await executor.close()
        await news_fetcher.close()
        journal.close()
        logger.info("Agent shutdown complete")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
