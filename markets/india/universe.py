from dataclasses import dataclass, field
from typing import List


@dataclass
class Stock:
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap_category: str
    isin: str
    exchange: str = "NSE"
    indices: List[str] = field(default_factory=list)


class UniverseEngine:
    """engine to manage and query the indian stock universe."""

    _stocks: List[Stock] = []

    @classmethod
    def load_universe(cls):
        """loads the predefined hardcoded universe of stocks."""
        if cls._stocks:
            return  # already loaded.

        cls._stocks = [
            Stock(
                "RELIANCE.NS",
                "Reliance Industries Ltd.",
                "Energy",
                "Oil & Gas",
                "Largecap",
                "INE002A01018",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "TCS.NS",
                "Tata Consultancy Services Ltd.",
                "IT",
                "IT Services",
                "Largecap",
                "INE467B01029",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "HDFCBANK.NS",
                "HDFC Bank Ltd.",
                "Banking",
                "Private Bank",
                "Largecap",
                "INE040A01034",
                "NSE",
                ["NIFTY_50", "BANK_NIFTY", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "ICICIBANK.NS",
                "ICICI Bank Ltd.",
                "Banking",
                "Private Bank",
                "Largecap",
                "INE090A01021",
                "NSE",
                ["NIFTY_50", "BANK_NIFTY", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "INFY.NS",
                "Infosys Ltd.",
                "IT",
                "IT Services",
                "Largecap",
                "INE009A01021",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "SBIN.NS",
                "State Bank of India",
                "Banking",
                "PSU Bank",
                "Largecap",
                "INE062A01020",
                "NSE",
                ["NIFTY_50", "BANK_NIFTY", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "BHARTIARTL.NS",
                "Bharti Airtel Ltd.",
                "Telecom",
                "Telecom Services",
                "Largecap",
                "INE397D01024",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "ITC.NS",
                "ITC Ltd.",
                "FMCG",
                "Tobacco & FMCG",
                "Largecap",
                "INE154A01025",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "HINDUNILVR.NS",
                "Hindustan Unilever Ltd.",
                "FMCG",
                "FMCG",
                "Largecap",
                "INE030A01027",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "SUNPHARMA.NS",
                "Sun Pharmaceutical Industries Ltd.",
                "Pharma",
                "Pharmaceuticals",
                "Largecap",
                "INE044A01036",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "BAJFINANCE.NS",
                "Bajaj Finance Ltd.",
                "Financial Services",
                "NBFC",
                "Largecap",
                "INE296A01024",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "AXISBANK.NS",
                "Axis Bank Ltd.",
                "Banking",
                "Private Bank",
                "Largecap",
                "INE238A01034",
                "NSE",
                ["NIFTY_50", "BANK_NIFTY", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "MARUTI.NS",
                "Maruti Suzuki India Ltd.",
                "Auto",
                "Automobiles",
                "Largecap",
                "INE585B01010",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "KOTAKBANK.NS",
                "Kotak Mahindra Bank Ltd.",
                "Banking",
                "Private Bank",
                "Largecap",
                "INE237A01028",
                "NSE",
                ["NIFTY_50", "BANK_NIFTY", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            Stock(
                "LT.NS",
                "Larsen & Toubro Ltd.",
                "Capital Goods",
                "Engineering & Construction",
                "Largecap",
                "INE018A01030",
                "NSE",
                ["NIFTY_50", "NIFTY_100", "NIFTY_200", "NIFTY_500", "SENSEX"],
            ),
            # non nifty but prominent mid next.
            Stock(
                "PNB.NS",
                "Punjab National Bank",
                "Banking",
                "PSU Bank",
                "Midcap",
                "INE160A01022",
                "NSE",
                ["NIFTY_NEXT_50", "BANK_NIFTY", "NIFTY_100", "NIFTY_200", "NIFTY_500"],
            ),
            Stock(
                "ZOMATO.NS",
                "Zomato Ltd.",
                "Consumer Services",
                "E-Commerce",
                "Largecap",
                "INE758T01015",
                "NSE",
                ["NIFTY_NEXT_50", "NIFTY_100", "NIFTY_200", "NIFTY_500"],
            ),
            Stock(
                "LUPIN.NS",
                "Lupin Ltd.",
                "Pharma",
                "Pharmaceuticals",
                "Midcap",
                "INE326A01037",
                "NSE",
                ["NIFTY_NEXT_50", "NIFTY_100", "NIFTY_200", "NIFTY_500"],
            ),
            Stock(
                "SUZLON.NS",
                "Suzlon Energy Ltd.",
                "Capital Goods",
                "Electrical Equipment",
                "Smallcap",
                "INE040H01021",
                "NSE",
                ["NIFTY_500", "SMALLCAP"],
            ),
            Stock(
                "IDEA.NS",
                "Vodafone Idea Ltd.",
                "Telecom",
                "Telecom Services",
                "Smallcap",
                "INE669E01016",
                "NSE",
                ["NIFTY_500", "SMALLCAP"],
            ),
        ]

    @classmethod
    def get_all_stocks(cls) -> List[Stock]:
        cls.load_universe()
        return cls._stocks

    @classmethod
    def get_by_index(cls, index_name: str) -> List[str]:
        cls.load_universe()
        idx_upper = index_name.upper()
        return [s.symbol for s in cls._stocks if idx_upper in s.indices]

    @classmethod
    def get_by_sector(cls, sector_name: str) -> List[str]:
        cls.load_universe()
        sec_upper = sector_name.upper()
        return [s.symbol for s in cls._stocks if s.sector.upper() == sec_upper]

    @classmethod
    def get_by_industry(cls, industry_name: str) -> List[str]:
        cls.load_universe()
        ind_upper = industry_name.upper()
        return [s.symbol for s in cls._stocks if s.industry.upper() == ind_upper]

    @classmethod
    def get_by_market_cap(cls, category: str) -> List[str]:
        cls.load_universe()
        cat_upper = category.upper()
        return [s.symbol for s in cls._stocks if s.market_cap_category.upper() == cat_upper]

    @classmethod
    def get_top_n(cls, n: int) -> List[str]:
        """returns top n stocks. since we don t have exact live market cap numbers in this hardcoded universe.
        we just return the first n largecap stocks as the hardcoded list is roughly sorted by prominence .
        """
        cls.load_universe()
        # in a real engine we d sort by actual market cap values.
        largecaps = [s.symbol for s in cls._stocks if s.market_cap_category.upper() == "LARGECAP"]
        return largecaps[:n]

    @classmethod
    def expand_symbol_list(cls, symbols: List[str]) -> List[str]:
        """takes a list of symbols which may contain magic keywords like index nifty.
        and returns a flat list of actual ticker strings."""
        expanded = set()
        for sym in symbols:
            if sym.upper().startswith("INDEX:"):
                idx_name = sym.split(":", 1)[1]
                expanded.update(cls.get_by_index(idx_name))
            elif sym.upper().startswith("SECTOR:"):
                sec_name = sym.split(":", 1)[1]
                expanded.update(cls.get_by_sector(sec_name))
            elif sym.upper().startswith("INDUSTRY:"):
                ind_name = sym.split(":", 1)[1]
                expanded.update(cls.get_by_industry(ind_name))
            elif sym.upper().startswith("CAP:"):
                cat_name = sym.split(":", 1)[1]
                expanded.update(cls.get_by_market_cap(cat_name))
            elif sym.upper().startswith("TOP:"):
                try:
                    n = int(sym.split(":", 1)[1])
                    expanded.update(cls.get_top_n(n))
                except ValueError:
                    pass  # ignore invalid top format.
            else:
                expanded.add(sym)

        # to maintain deterministic order sort them.
        return sorted(list(expanded))


def get_universe_tickers(query: str) -> list[str]:
    """helper function to parse a single shortcut string e.g. index nifty ."""
    return UniverseEngine.expand_symbol_list([query])
