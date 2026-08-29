class MarketDataUnavailable(Exception):
    """Raised when a provider cannot produce a usable price for a ticker."""

    def __init__(self, ticker: str, reason: str):
        self.ticker = ticker
        self.reason = reason
        super().__init__(f"no usable price for {ticker}: {reason}")
