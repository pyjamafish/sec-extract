from bs4 import BeautifulSoup, Tag
import functools
import logging
import sys

BEFORE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
    <meta http-equiv="Content-Type" content="text/html;charset=UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
"""

AFTER = """</body>
</html>
"""


class SectionAnchorNotFoundError(Exception):
    def __init__(self, section_name: str):
        super().__init__(section_name)
        self.section_name = section_name

    def __str__(self):
        return f"\"{self.section_name}\" section anchor not found"


class MissingNamedAnchorError(Exception):
    def __init__(self, section_name: str):
        super().__init__(section_name)
        self.section_name = section_name

    def __str__(self):
        return f"Missing named anchor for \"{self.section_name}\""


class IncompatibleTableOfContentsError(Exception):
    pass


def is_start_anchor_for_section(tag, section_name: str) -> bool:
    try:
        return (
            tag.name == "a"
            and (
                tag.text.lower().strip() == section_name
            )
        )
    except AttributeError:
        return False


def is_start_anchor_for_different_section(tag, old_href) -> bool:
    try:
        if tag.name == "a" and tag.text != "" and not tag.text.isdigit():
            if ("href", old_href) in tag.attrs.items():
                raise IncompatibleTableOfContentsError

            return True
    except AttributeError:
        return False


def get_anchor_names(soup: BeautifulSoup, section_name: str) -> (str, str):
    try:
        start_anchor = soup.find(
            functools.partial(is_start_anchor_for_section, section_name=section_name)
        )
        end_anchor = start_anchor.find_next(
            functools.partial(is_start_anchor_for_different_section, old_href=start_anchor.attrs["href"])
        )
    except AttributeError:
        raise SectionAnchorNotFoundError(section_name)

    start_anchor_name = start_anchor.attrs["href"].replace("#", "")
    end_anchor_name = end_anchor.attrs["href"].replace("#", "")

    return start_anchor_name, end_anchor_name


def extract_between_tags(soup: BeautifulSoup, start_tag, end_tag) -> str:
    soup_string = str(soup)
    start_index = soup_string.index(str(start_tag))
    end_index = soup_string.index(str(end_tag))
    return soup_string[start_index: end_index]


def find_parent_with_siblings(tag) -> Tag:
    if any(isinstance(sibling, Tag) for sibling in tag.next_siblings):
        return tag
    else:
        return find_parent_with_siblings(tag.parent)


def extract_section(soup: BeautifulSoup, section_name: str) -> str:
    start_anchor_name, end_anchor_name = get_anchor_names(soup, section_name)

    start_anchor = soup.find("a", attrs={"name": start_anchor_name})
    end_anchor = soup.find("a", attrs={"name": end_anchor_name})

    if start_anchor is None or end_anchor is None:
        raise MissingNamedAnchorError(section_name)

    return extract_between_tags(
        soup,
        find_parent_with_siblings(start_anchor),
        find_parent_with_siblings(end_anchor)
    )


def extract_section_and_save(soup: BeautifulSoup, ticker: str, section_name: str) -> bool:
    try:
        section = extract_section(soup, section_name)
    except SectionAnchorNotFoundError as e:
        logging.warning(f"\"{e.section_name}\" section anchor not found for {ticker}")
        return False
    except MissingNamedAnchorError as e:
        logging.warning(f"Missing named anchor for \"{e.section_name}\" for {ticker}")
        return False
    except IncompatibleTableOfContentsError:
        logging.warning(f"Incompatible table of contents for {ticker}")
        return False

    with open(f"s1_{section_name}/{ticker}.html", "w") as f:
        f.write(BEFORE)
        f.write(section)
        f.write(AFTER)
    return True


def main():
    tickers = [
        "BCC",
        "FIVN",
        "CMG",
        "WIFI",
        "NTLA",
        "KBR",
        "FMSA",
        "EGLT",
        "VAPO",
        "MRC",
        "VISN",
        "SMOD",
        "N",
        "LRE"
    ]
    logging.basicConfig(level="DEBUG")
    sys.setrecursionlimit(10000)  # Required to cast soup objects to strings
    for ticker in tickers:
        logging.info(f"Now extracting {ticker}")
        with open(f"../download/s1_html/{ticker}.html") as f:
            soup = BeautifulSoup(f, "html.parser")

        extract_section_and_save(soup, ticker, "business")
        extract_section_and_save(soup, ticker, "management")


if __name__ == "__main__":
    main()
