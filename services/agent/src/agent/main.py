from __future__ import annotations

import asyncio
import logging
import sys

from agent.config import AgentSettings
from agent.executor import TradeExecutor
from agent.feedback import FeedbackAnalyzer
from agent.llm import LLMClient
from agent.market_analyzer import MarketAnalyzer
from agent.prompt_builder import PromptBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent")


async def run_cycle(
    settings: AgentSettings,
    llm: LLMClient,
    analyzer: MarketAnalyzer,
    builder: PromptBuilder,
    executor: TradeExecutor,
    feedback: FeedbackAnalyzer,
    cycle: int,
) -> None:
    """Execute a single analysis-trade cycle for all configured symbols."""
    logger.info("=== Cycle %d started ===", cycle)

    portfolio = await analyzer.get_portfolio_state()

    risk_constraints = {
        "max_position_pct": settings.max_position_pct,
        "stop_loss_pct": settings.stop_loss_pct,
        "initial_capital": settings.initial_capital,
    }

    for symbol in settings.symbols:
        logger.info("Analyzing %s ...", symbol)

        # 1. Get market state
        market_summary = await analyzer.get_market_summary(symbol)

        # 2. Build prompt
        prompt = builder.build(
            persona=settings.persona,
            market_summary=market_summary,
            portfolio=portfolio,
            risk_constraints=risk_constraints,
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

        # 4. Execute decisions
        for d in decision.get("decisions", []):
            if d.get("action") == "hold":
                logger.info("Hold %s (confidence=%.2f)", d.get("symbol", symbol), d.get("confidence", 0))
                continue
            result = await executor.execute(d)
            logger.info(
                "Execution result for %s %s: %s",
                d.get("action"),
                d.get("symbol", symbol),
                result.get("status"),
            )

    # 5. Periodic feedback review (every 6 cycles)
    if cycle > 0 and cycle % 6 == 0:
        logger.info("Running performance review ...")
        trades = await analyzer.get_recent_trades(limit=50)
        review = await feedback.review_performance(llm, trades, portfolio)
        logger.info("Performance review: %s", review.get("review", "")[:300])

    logger.info("=== Cycle %d completed ===", cycle)


async def run() -> None:
    settings = AgentSettings()

    # Validate API key
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

    cycle = 0
    try:
        while True:
            try:
                await run_cycle(
                    settings,
                    llm,
                    analyzer,
                    builder,
                    executor,
                    feedback_analyzer,
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
        logger.info("Agent shutdown complete")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
