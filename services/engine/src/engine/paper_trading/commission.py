from abc import ABC, abstractmethod

from engine.strategies.base import Market


class CommissionModel(ABC):
    """Base commission model."""

    @abstractmethod
    def calculate(
        self, price: float, quantity: float, is_sell: bool = False
    ) -> float: ...


class AStockCommission(CommissionModel):
    """A-share commission: 0.03% both sides + 0.05% stamp tax on sell."""

    def __init__(
        self,
        rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_tax: float = 0.0005,
    ) -> None:
        self.rate = rate
        self.min_commission = min_commission
        self.stamp_tax = stamp_tax

    def calculate(self, price: float, quantity: float, is_sell: bool = False) -> float:
        notional = price * quantity
        commission = max(notional * self.rate, self.min_commission)
        if is_sell:
            commission += notional * self.stamp_tax
        return round(commission, 2)


class CryptoCommission(CommissionModel):
    """Binance-style commission: 0.1% maker/taker."""

    def __init__(self, rate: float = 0.001) -> None:
        self.rate = rate

    def calculate(self, price: float, quantity: float, is_sell: bool = False) -> float:
        return round(price * quantity * self.rate, 8)


class USStockCommission(CommissionModel):
    """US stock zero-commission broker + SEC fee on sells."""

    SEC_FEE_RATE = 8.0 / 1_000_000  # $8 per million

    def calculate(self, price: float, quantity: float, is_sell: bool = False) -> float:
        if is_sell:
            notional = price * quantity
            return round(notional * self.SEC_FEE_RATE, 4)
        return 0.0


def get_commission_model(market: Market) -> CommissionModel:
    models: dict[Market, CommissionModel] = {
        Market.A_STOCK: AStockCommission(),
        Market.CRYPTO: CryptoCommission(),
        Market.US_STOCK: USStockCommission(),
    }
    return models[market]
