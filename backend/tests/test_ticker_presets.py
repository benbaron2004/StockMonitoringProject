from app.config import TICKER_PRESETS


def test_no_duplicate_symbols():
    symbols = [p.symbol for p in TICKER_PRESETS]
    assert len(symbols) == len(set(symbols))


def test_all_symbols_are_tase_tickers():
    for p in TICKER_PRESETS:
        assert p.symbol.endswith(".TA"), f"{p.symbol} is not a TASE (.TA) ticker"


def test_all_presets_have_a_name():
    for p in TICKER_PRESETS:
        assert p.name.strip()


def test_expanded_beyond_original_six():
    # Sanity check that the TA-125 expansion actually took effect.
    assert len(TICKER_PRESETS) > 50
