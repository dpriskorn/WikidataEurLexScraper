"""This is a tool for scraping information from Eur-Lex
https://www.wikidata.org/wiki/Property:P476 is the CELEX property
query https://query.wikidata.org/#SELECT%20%28COUNT%28%3Fitem%29%20AS%20%3Fcount%29%0AWHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP476%20%3Fvalue.%0A%7D%0A
There are 4594 items with this identifier right now.
It currently only scrapes the name of the law"""
import logging
from typing import List

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_helpers import execute_sparql_query
from wikibaseintegrator.wbi_config import config as wbconfig
from wikibaseintegrator.wbi_login import Login

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
wbconfig["USER_AGENT"] = "WikidataEurLexScraper by So9q"


class Title(BaseModel):
    title: str
    language: str

    @property
    def longer_than_wikidata_support(self):
        return bool(len(self.title) > 250)


class LawItem(BaseModel):
    wbi: WikibaseIntegrator
    item_id: str
    celex_id: str
    titles: List[Title] = list()
    languages: List[str] = [
        "BG",
        "ES",
        "CS",
        "DA",
        "DE",
        "ET",
        "EL",
        "EN",
        "FR",
        "GA",
        "HR",
        "IT",
        "LV",
        "LT",
        "HU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SL",
        "FI",
        "SV",
    ]

    class Config:
        arbitrary_types_allowed = True

    def start(self):
        self.scrape_law_titles()
        self.enrich_wikidata()

    def enrich_wikidata(self):
        something_to_upload = False
        item = self.wbi.item.get(entity_id=self.item_id)
        for language in self.languages:
            language_lower = language.lower()
            title_already_in_wikidata = False
            title_for_this_language = None
            has_label = False
            for title in self.titles:
                if title.language == language:
                    if title.longer_than_wikidata_support:
                        print(f"title too long: '{title.title}'")
                    else:
                        title_for_this_language = title
            label = item.labels.get(language=language.lower())
            if label:
                has_label = True
                if label == title_for_this_language.title:
                    print("label for this language in "
                          "wikidata mathches the title, skipping")
                    title_already_in_wikidata = True
                    break
                else:
                    print(label)
                print("checking aliases")
                aliases = item.aliases.get(language=language_lower)
                if aliases:
                    print(aliases)
                    for alias in aliases:
                        if alias == title_for_this_language.title:
                            title_already_in_wikidata = True
            if not title_already_in_wikidata:
                something_to_upload = True
                # we are missing this data in Wikidata, lets add it
                if not has_label:
                    # add as label
                    item.labels.set(value=title_for_this_language.title,
                                    language=language_lower)
                else:
                    # add as alias
                    item.aliases.set(values=[title_for_this_language.title],
                                     language=language_lower)
            else:
                print("this title is already in Wikidata")
        if something_to_upload:
            input("press enter to upload")
            item.write(summary="Adding labels and aliases "
                               "with WikidataEurLexScraper")

    def scrape_law_titles(self):
        print(f"Fetching law titles for {self.celex_id}")
        for language in self.languages:
            # Construct the URL based on the CELEX identifier
            url = (f"https://eur-lex.europa.eu/legal-content/{language}"
                   f"/TXT/?uri=CELEX:{self.celex_id}")
            logger.info(f"Fetching {url}")
            # Send a GET request to the URL
            response = requests.get(url)

            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                # Parse the HTML content using BeautifulSoup
                soup = BeautifulSoup(response.content, "html.parser")

                # Find the element containing the law title using the provided jQuery selector
                law_title = soup.select_one("p#title").get_text(strip=True)
                if law_title:
                    self.titles.append(Title(title=law_title, language=language))
                else:
                    raise ValueError(f"no law title found, see {url}")
            else:
                logger.info(f"got {response.status_code} from eur-lex")


class EurlexScraper(BaseModel):
    sparql_query: str = """
    SELECT ?item ?celex_id
    WHERE {
      ?item wdt:P476 ?celex_id.
    }
    """
    items: List[LawItem] = []
    wbi: WikibaseIntegrator

    class Config:
        arbitrary_types_allowed = True

    def start(self):
        self.fetch_items()
        self.iterate_items()

    def fetch_items(self):
        query = execute_sparql_query(self.sparql_query)

        # Fetching items from the query result
        for result in query['results']['bindings']:
            item_id = self.get_stripped_qid(id=str(result['item']['value']))
            celex_id = result['celex_id']['value']
            self.items.append(LawItem(item_id=item_id, celex_id=celex_id, wbi=self.wbi))

    def iterate_items(self):
        for item in self.items:
            item.start()
            exit()

    @staticmethod
    def get_stripped_qid(id: str) -> str:
        return id.replace("http://www.wikidata.org/entity/", "")


# Example usage:
# celex_id = "32012L0013"
wbi = WikibaseIntegrator(login=Login(
    user=config.user_name,
    password=config.bot_password))
scraper = EurlexScraper(wbi=wbi)
scraper.start()
# item = LawItem(item_id="", celex_id=celex_id, wbi=wbi)
# item.start()
# for title in item.titles:
#     print(f"The law title for CELEX:{celex_id} "
#           f"and language {title.language} is: {title.title}")
