from markets.india.universe import UniverseEngine


def test_universe_loading():
    stocks = UniverseEngine.get_all_stocks()
    assert len(stocks) > 0

    # check that reliance is loaded.
    rel = [s for s in stocks if s.symbol == "RELIANCE.NS"]
    assert len(rel) == 1
    assert "Energy" in rel[0].sector


def test_get_by_index():
    nifty50 = UniverseEngine.get_by_index("NIFTY_50")
    assert "RELIANCE.NS" in nifty50
    assert "TCS.NS" in nifty50
    assert "ZOMATO.NS" not in nifty50  # it s in next in our hardcoded set.

    bank_nifty = UniverseEngine.get_by_index("BANK_NIFTY")
    assert "HDFCBANK.NS" in bank_nifty
    assert "ICICIBANK.NS" in bank_nifty
    assert "RELIANCE.NS" not in bank_nifty


def test_get_by_sector():
    it_stocks = UniverseEngine.get_by_sector("IT")
    assert "TCS.NS" in it_stocks
    assert "INFY.NS" in it_stocks
    assert "RELIANCE.NS" not in it_stocks


def test_expand_symbol_list():
    raw_list = ["INDEX:BANK_NIFTY", "RELIANCE.NS", "SECTOR:IT"]
    expanded = UniverseEngine.expand_symbol_list(raw_list)

    assert "HDFCBANK.NS" in expanded
    assert "ICICIBANK.NS" in expanded
    assert "RELIANCE.NS" in expanded
    assert "TCS.NS" in expanded
    assert "INFY.NS" in expanded

    # assert deduplication.
    assert len(expanded) == len(set(expanded))


def test_expand_top_n():
    raw_list = ["TOP:5"]
    expanded = UniverseEngine.expand_symbol_list(raw_list)
    assert len(expanded) == 5
