from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Executes trade decisions by calling the Kainex Engine API."""

    def __init__(self, engine_api_url: str) -> None:
        self._engine_url = engine_api_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self._engine_url, timeout=30.0)
        self._trade_log: list[dict] = []

    async def execute(self, decision: dict) -> dict:
        """Execute a single trade decision.

        *decision* should contain at least: action, symbol, quantity.
        Optional: stop_loss, take_profit, reason, confidence.

        Returns a dict with execution status.
        """
        action = decision.get("action", "hold")
        if action == "hold":
            return {"status": "skipped", "reason": "hold"}

        symbol = decision.get("symbol", "")
        quantity = decision.get("quantity", 0.0)

        if not symbol or quantity <= 0:
            logger.warning("Invalid decision skipped: %s", decision)
            return {"status": "skipped", "reason": "invalid symbol or quantity"}

        side = "buy" if action == "buy" else "sell"

        # Record the trade via the Engine API /api/portfolio/trades endpoint.
        # The engine doesn't expose a direct order-submission endpoint yet, so
        # we POST a trade record that the paper broker can pick up.
        trade_payload = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "reason": decision.get("reason", ""),
            "confidence": decision.get("confidence", 0.0),
            "stop_loss": decision.get("stop_loss"),
            "take_profit": decision.get("take_profit"),
            "source": "ai-agent",
        }

        try:
            # Attempt to submit via Engine API
            resp = await self._http.post(
                "/api/portfolio/trades",
                json=trade_payload,
            )
            if resp.status_code in (200, 201):
                result = {
                    "status": "executed",
                    "trade": resp.json(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Engine may not support direct trade submission yet.
                # Log the decision for manual review.
                result = {
                    "status": "logged",
                    "reason": f"Engine returned {resp.status_code}",
                    "decision": trade_payload,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                logger.info(
                    "Trade logged (engine returned %d): %s %s %.4f %s",
                    resp.status_code,
                    side,
                    symbol,
                    quantity,
                    decision.get("reason", ""),
                )
        except httpx.HTTPError as exc:
            result = {
                "status": "failed",
                "error": str(exc),
                "decision": trade_payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.error("Trade execution failed: %s", exc)

        self._trade_log.append(result)
        return result

    @property
    def trade_log(self) -> list[dict]:
        return list(self._trade_log)

    async def close(self) -> None:
        await self._http.aclose()
