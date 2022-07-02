import csv
import logging
from collections import namedtuple
from concurrent import futures

from sec_api import QueryApi, RenderApi
from sec_extract.keys import SEC_API_KEY

QUERY_API = QueryApi(SEC_API_KEY)
RENDER_API = RenderApi(SEC_API_KEY)

THREADS = 8


class FormNotFoundError(Exception):
    pass


Firm = namedtuple("Firm", ("ticker_symbol", "year", "cusip"))

Form = namedtuple("Form", ("text", "basename"))


def get_firms() -> list[Firm]:
    with open("IPO Firm list 2005-2019.csv") as f:
        reader = csv.reader(f)
        reader.__next__()  # Skip first row
        firms = [Firm(*row) for row in reader]
    return firms


def get_s1_url(ticker: str) -> str:
    query = {
        "query": {
            "query_string": {
                "query": f"ticker:{ticker} AND formType:\"S-1\""
            }
        },
        "from": "0",
        "size": "1",
        "sort": [{"filedAt": {"order": "asc"}}]
    }
    filings = QUERY_API.get_filings(query)
    try:
        return filings["filings"][0]["linkToFilingDetails"].replace("ix?doc=/", "")
    except IndexError:
        raise FormNotFoundError(f"No S-1 found for {ticker}")


def get_10k_url(ticker: str, year: int) -> str:
    year_range = f"[{year}-01-01T00:00:00 TO {year + 1}-01-01T00:00:00]"
    query = {
        "query": {
            "query_string": {
                "query": f"ticker:{ticker} AND formType:\"10-K\" AND filedAt: {year_range}",
                "time_zone": "America/New_York"
            }
        },
        "from": "0",
        "size": "1",
        "sort": [{"filedAt": {"order": "desc"}}]
    }
    filings = QUERY_API.get_filings(query)
    try:
        return filings["filings"][0]["linkToFilingDetails"].replace("ix?doc=/", "")
    except IndexError:
        raise FormNotFoundError(f"No 10-K found for {ticker} in range {year_range}")


def get_s1(firm: Firm) -> Form:
    logging.info(f"Fetching S-1 for {firm.ticker_symbol}")
    text = RENDER_API.get_filing(get_s1_url(firm.ticker_symbol))
    basename = f"{firm.ticker_symbol}.html"
    return Form(text, basename)


def get_10k(firm: Firm, years_after_ipo: int) -> Form:
    if firm.year == "":
        raise ValueError(f"Firm \"{firm.ticker_symbol}\" is missing IPO year")

    document_year = int(firm.year) + years_after_ipo
    logging.info(f"Fetching 10-K for {firm.ticker_symbol}, year {document_year}")
    text = RENDER_API.get_filing(get_10k_url(firm.ticker_symbol, document_year))
    basename = f"{firm.ticker_symbol}{document_year}.html"
    return Form(text, basename)


def save_to_file(s: str, destination_path: str) -> None:
    with open(destination_path, "w") as f:
        f.write(s)
    logging.info(f"Saved {destination_path}")


def download_all_s1s(firms: list[Firm]) -> None:
    with futures.ThreadPoolExecutor(THREADS) as executor:
        futures_list = [
            executor.submit(get_s1, firm)
            for firm in firms
        ]

        for future in futures_list:
            if future.exception():
                logging.warning(future.exception())
                continue

            form = future.result()
            save_to_file(
                form.text,
                f"s1_html/{form.basename}"
            )


def download_all_10ks(firms: list[Firm]) -> None:
    with futures.ThreadPoolExecutor(THREADS) as executor:
        futures_list = [
            executor.submit(get_10k, firm, i)
            for i in range(3, 6)
            for firm in firms
        ]

        for future in futures_list:
            if future.exception() is not None:
                logging.warning(future.exception())
                continue

            form = future.result()
            save_to_file(
                form.text,
                f"10k_html/{form.basename}"
            )


def main() -> None:
    logging.basicConfig(level="INFO")
    firms = get_firms()

    download_all_s1s(firms)


if __name__ == "__main__":
    main()
