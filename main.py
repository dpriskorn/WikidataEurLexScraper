"""This is a tool for scraping information from Eur-Lex
https://www.wikidata.org/wiki/Property:P476 is the CELEX property
query https://query.wikidata.org/#SELECT%20%28COUNT%28%3Fitem%29%20AS%20%3Fcount%29%0AWHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP476%20%3Fvalue.%0A%7D%0A
There are 4594 items with this identifier right now.
It currently only scrapes the name of the law"""
import logging
import sqlite3
from typing import List, Any

import requests
from bs4 import BeautifulSoup
from ftlangdetect import detect
from pydantic import BaseModel
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbconfig
from wikibaseintegrator.wbi_helpers import execute_sparql_query
from wikibaseintegrator.wbi_login import Login

import config

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)
wbconfig["USER_AGENT"] = config.user_agent


class Title(BaseModel):
    title: str
    language: str
    detected_language: str = ""
    score: float = 0.0

    @property
    def longer_than_wikidata_support(self) -> bool:
        return bool(len(self.title) > 250)

    def detect_language(self) -> None:
        # This returns a dict like so: {'lang': 'tr', 'score': 0.9982126951217651}
        language_result = detect(text=self.title, low_memory=False)
        self.detected_language = language_result["lang"]
        self.score = language_result["score"]
        if self.accepted_title:
            logger.info(f"got good title for language {self.detected_language}")
        else:
            if self.languages_match:
                logger.info(f"got title we do not accept because of low score of {self.score} for {self.detected_language}")
            else:
                logger.info(f"Eur-Lex language {self.language} and detected language {self.detected_language} did not match")
                logger.debug(f"for title {self.title} with score: {self.score}")

    @property
    def languages_match(self) -> bool:
        return bool(self.language.lower() == self.detected_language)

    @property
    def accepted_title(self) -> bool:
        """We accept scores over 0.4 for mt and 0.7 for all others"""
        if self.languages_match:
            if self.detected_language == "mt" and self.score > 0.4:
                return True
            elif self.detected_language != "mt" and self.score > 0.7:
                return True
        return False


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
        print(item.get_entity_url())
        for language in self.languages:
            language_lower = language.lower()
            title_already_in_wikidata = False
            title_for_this_language = None
            has_label = False
            for title in self.titles:
                if title.language == language:
                    if title.longer_than_wikidata_support:
                        logger.info(f"title too long: '{title.title}'")
                    else:
                        title_for_this_language = title
            if title_for_this_language is not None:
                label = item.labels.get(language=language.lower())
                if label:
                    has_label = True
                    if label == title_for_this_language.title:
                        logger.info(f"label for {language_lower} in "
                                    "wikidata mathches the title, skipping this language")
                        title_already_in_wikidata = True
                    if not title_already_in_wikidata:
                        logger.info(f"checking {language_lower} aliases")
                        aliases = item.aliases.get(language=language_lower)
                        if aliases:
                            logger.info(aliases)
                            for alias in aliases:
                                if alias == title_for_this_language.title:
                                    title_already_in_wikidata = True
                if not title_already_in_wikidata:  # and title_for_this_language.title
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
                    logger.info("this title is already in Wikidata")
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
                # Guard against None
                if law_title and law_title is not None:
                    title = Title(title=law_title, language=language)
                    title.detect_language()
                    if title.accepted_title:
                        self.titles.append(title)
                else:
                    raise ValueError(f"no law title found, see {url}")
            else:
                logger.info(f"got {response.status_code} from eur-lex")


class EurlexScraper(BaseModel):
    conn: Any = None
    cursor: Any = None
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
        self.connect()
        self.get_cursor()
        self.create_db()
        self.get_count_of_done_item_ids()
        self.iterate_items()
        self.conn.close()

    def fetch_items(self):
        query = execute_sparql_query(self.sparql_query)

        # Fetching items from the query result
        for result in query['results']['bindings']:
            item_id = self.get_stripped_qid(item_id=str(result['item']['value']))
            celex_id = result['celex_id']['value']
            self.items.append(LawItem(item_id=item_id, celex_id=celex_id, wbi=self.wbi))

    def iterate_items(self):
        for item in self.items:
            item_id = int(item.item_id[1:])
            if not self.already_processed(item_id=item_id):
                item.start()
                self.add_item_id_to_database(item_id=item_id)
                # exit()
            else:
                print(f"{item.item_id} has already been processed")

    def already_processed(self, item_id) -> bool:
        self.cursor.execute('SELECT COUNT(item_id) FROM processed WHERE item_id = ?', (item_id,))
        count = self.cursor.fetchone()[0]
        return bool(count > 0)

    @staticmethod
    def get_stripped_qid(item_id: str) -> str:
        return item_id.replace("http://www.wikidata.org/entity/", "")

    def connect(self):
        # Connect to a database (creates if not exists)
        self.conn = sqlite3.connect('database.db')

    def get_cursor(self):
        # Create a cursor object to execute SQL commands
        self.cursor = self.conn.cursor()

    def create_db(self):
        # Create a table named 'processed' with a column 'item_id'
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed (
                item_id INTEGER PRIMARY KEY
            )
        ''')

        # Create an index on the 'item_id' column
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_item_id ON processed (item_id)
        ''')

        # Commit changes and close the connection
        self.conn.commit()

    def add_item_id_to_database(self, item_id: int):
        # try:
        self.cursor.execute('''
            INSERT INTO processed (item_id) VALUES (?)
        ''', (item_id,))
        # except IntegrityError:
        #     # skip silently if item_id already exists
        #     pass
        self.conn.commit()

    def get_count_of_done_item_ids(self):
        self.cursor.execute('SELECT COUNT(item_id) FROM processed')
        count = self.cursor.fetchone()[0]
        print(f"{count} item_ids found in the database")


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
