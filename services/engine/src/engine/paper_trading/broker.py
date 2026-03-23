from dataclasses import dataclass
from datetime import datetime, timezone, date
from enum import Enum

from engine.paper_trading.commission import CommissionModel, get_commission_model
from engine.paper_trading.slippage import SlippageModel
from engine.risk.manager import RiskManager
from engine.strategies.base import Market, Signal, SignalType


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    id: str
    symbol: str
    side: SignalType
    quantity: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    commission: float = 0.0
    filled_at: datetime | None = None
    reject_reason: str = ""


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    market_price: float = 0.0
    unrealized_pnl: float = 0.0
    buy_date: date | None = None


class PaperBroker:
    """Simulated order execution with slippage, commission, and risk management."""

    def __init__(
        self,
        market: Market = Market.A_STOCK,
        initial_cash: float = 100_000.0,
        slippage: SlippageModel | None = None,
        commission: CommissionModel | None = None,
        risk_manager: RiskManager | None = None,
    ) -> None:
        self.market = market
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.slippage = slippage or SlippageModel()
        self.commission = commission or get_commission_model(market)
        self.risk_manager = risk_manager
        self.positions: dict[str, Position] = {}
        self.orders: list[Order] = []
        self._order_counter = 0
        self._current_date: date | None = None
        self._peak_equity: float = initial_cash

    def set_current_date(self, dt: date) -> None:
        """Set the current simulation date (for T+1 enforcement)."""
        self._current_date = dt

    def update_market_price(self, symbol: str, price: float) -> None:
        """Update the market price for a held position."""
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.market_price = price
            pos.unrealized_pnl = (price - pos.avg_price) * pos.quantity

    def submit_order(self, signal: Signal) -> Order:
        """Submit and immediately fill a market order."""
        self._order_counter += 1
        order = Order(
            id=f"PT-{self._order_counter:06d}",
            symbol=signal.symbol,
            side=signal.signal_type,
            quantity=signal.quantity,
            price=signal.price,
        )

        # Risk check
        if self.risk_manager and signal.signal_type == SignalType.BUY:
            pos_value = 0.0
            if signal.symbol in self.positions:
                pos = self.positions[signal.symbol]
                pos_value = pos.quantity * (pos.market_price or pos.avg_price)
            if not self.risk_manager.check(signal, self.equity, pos_value):
                order.status = OrderStatus.REJECTED
                order.reject_reason = "risk check failed"
                self.orders.append(order)
                return order

        # A-stock T+1 rule: cannot sell shares bought on the same day
        if (
            self.market == Market.A_STOCK
            and signal.signal_type == SignalType.SELL
            and self._current_date is not None
        ):
            pos = self.positions.get(signal.symbol)
            if pos and pos.buy_date == self._current_date:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "T+1 rule: cannot sell shares bought today"
                self.orders.append(order)
                return order

        self._fill(order)
        self.orders.append(order)

        # Update peak equity for risk manager
        if self.risk_manager:
            current_eq = self.equity
            if current_eq > self._peak_equity:
                self._peak_equity = current_eq
            self.risk_manager.update_equity(current_eq, self._peak_equity)

        return order

    def _fill(self, order: Order) -> None:
        fill_price = self.slippage.apply(order.price, order.side)
        is_sell = order.side == SignalType.SELL
        comm = self.commission.calculate(fill_price, order.quantity, is_sell=is_sell)

        cost = fill_price * order.quantity
        if order.side == SignalType.BUY:
            if self.cash < cost + comm:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "insufficient cash"
                return
            self.cash -= cost + comm
            pos = self.positions.setdefault(order.symbol, Position(symbol=order.symbol))
            total_cost = pos.avg_price * pos.quantity + cost
            pos.quantity += order.quantity
            pos.avg_price = total_cost / pos.quantity if pos.quantity > 0 else 0.0
            pos.market_price = fill_price
            if self._current_date is not None:
                pos.buy_date = self._current_date
        elif order.side == SignalType.SELL:
            pos = self.positions.get(order.symbol)
            if not pos or pos.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "insufficient position"
                return
            self.cash += cost - comm
            pos.quantity -= order.quantity
            if pos.quantity == 0:
                del self.positions[order.symbol]

        order.filled_price = fill_price
        order.commission = comm
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now(timezone.utc)

    @property
    def equity(self) -> float:
        """Total equity = cash + sum of positions valued at market price."""
        position_value = sum(
            p.quantity * (p.market_price if p.market_price > 0 else p.avg_price)
            for p in self.positions.values()
        )
        return self.cash + position_value
