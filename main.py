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
from wikibaseintegrator.datatypes import MonolingualText, URL, Time
from wikibaseintegrator.entities import ItemEntity
from wikibaseintegrator.models import References, Qualifiers
from wikibaseintegrator.wbi_config import config as wbconfig
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_helpers import execute_sparql_query
from wikibaseintegrator.wbi_login import Login

import config

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)
wbconfig["USER_AGENT"] = config.user_agent


class Title(BaseModel):
    title: str
    language: str
    celex_id: str
    detected_language: str = ""
    score: float = 0.0

    @property
    def eurlex_url(self):
        return (
            f"https://eur-lex.europa.eu/legal-content/{self.language}"
            f"/TXT/?uri=CELEX:{self.celex_id}"
        )

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
                logger.info(
                    f"got title we do not accept because of low score of {self.score} for {self.detected_language}"
                )
            else:
                logger.info(
                    f"Eur-Lex language {self.language} and detected language {self.detected_language} did not match"
                )
                logger.debug(f"for title {self.title} with score: {self.score}")

    @property
    def languages_match(self) -> bool:
        return bool(self.language.lower() == self.detected_language)

    @property
    def accepted_title(self) -> bool:
        """We accept scores over 0.4 for all languages"""
        if self.languages_match:
            if self.score > 0.4:
                return True
        return False


class LawItem(BaseModel):
    something_to_upload: bool = False
    item: ItemEntity = None
    wbi: WikibaseIntegrator
    item_id: str
    celex_id: str
    accepted_titles: List[Title] = list()
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
        self.item = self.wbi.item.get(entity_id=self.item_id)
        print(self.item.get_entity_url())
        self.add_labels_and_aliases()
        self.add_name_statements()
        if self.something_to_upload:
            input("press enter to upload")
            self.item.write(
                summary="Adding names with [[Wikidata:Tools/WikidataEurLexScraper|WikidataEurLexScraper]]"
            )

    def add_name_statements(self):
        print("Adding name-statements")
        for title in self.accepted_titles:
            self.something_to_upload = True
            self.add_name_claim(title=title)

    def add_labels_and_aliases(self):
        print("Adding labels and aliases")
        for language in self.languages:
            language_lower = language.lower()
            title_already_in_wikidata = False
            title_for_this_language = None
            has_label = False
            for title in self.accepted_titles:
                if title.language == language:
                    if title.longer_than_wikidata_support:
                        logger.info(f"title too long: '{title.title}'")
                    else:
                        title_for_this_language = title
            if title_for_this_language is not None:
                label = self.item.labels.get(language=language.lower())
                if label:
                    has_label = True
                    if label == title_for_this_language.title:
                        logger.info(
                            f"label for {language_lower} in "
                            "wikidata mathches the title, skipping this language"
                        )
                        title_already_in_wikidata = True
                    if not title_already_in_wikidata:
                        logger.info(f"checking {language_lower} aliases")
                        aliases = self.item.aliases.get(language=language_lower)
                        if aliases:
                            logger.info(aliases)
                            for alias in aliases:
                                if alias == title_for_this_language.title:
                                    title_already_in_wikidata = True
                if not title_already_in_wikidata:  # and title_for_this_language.title
                    self.something_to_upload = True
                    # we are missing this data in Wikidata, lets add it
                    if not has_label:
                        # add as label
                        self.item.labels.set(
                            value=title_for_this_language.title, language=language_lower
                        )
                    else:
                        # add as alias
                        self.item.aliases.set(
                            values=[title_for_this_language.title],
                            language=language_lower,
                        )
                else:
                    logger.info("this title is already in Wikidata")

    def add_name_claim(self, title: Title):
        # logger.info("Add name statement")
        self.item.claims.add(claims=[MonolingualText(
                prop_nr="P1448",  # official name
                language=title.language.lower(),
                text=title.title,
                references=References().add(
                    URL(
                        prop_nr="P854",  # reference URL
                        value=title.eurlex_url,
                        qualifiers=Qualifiers().add(Time(prop_nr="P813",  # retrieved
                                                         time="now")),
                    )
                ),
            )],
            action_if_exists=ActionIfExists.KEEP,
        )

    def scrape_law_titles(self):
        print(f"Fetching law titles for {self.celex_id}")
        for language in self.languages:
            # Construct the URL based on the CELEX identifier
            url = (
                f"https://eur-lex.europa.eu/legal-content/{language}"
                f"/TXT/?uri=CELEX:{self.celex_id}"
            )
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
                    title = Title(
                        title=law_title, language=language, celex_id=self.celex_id
                    )
                    title.detect_language()
                    if title.accepted_title:
                        self.accepted_titles.append(title)
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
        for result in query["results"]["bindings"]:
            item_id = self.get_stripped_qid(item_id=str(result["item"]["value"]))
            celex_id = result["celex_id"]["value"]
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
        self.cursor.execute(
            "SELECT COUNT(item_id) FROM processed WHERE item_id = ?", (item_id,)
        )
        count = self.cursor.fetchone()[0]
        return bool(count > 0)

    @staticmethod
    def get_stripped_qid(item_id: str) -> str:
        return item_id.replace("http://www.wikidata.org/entity/", "")

    def connect(self):
        # Connect to a database (creates if not exists)
        self.conn = sqlite3.connect("database.db")

    def get_cursor(self):
        # Create a cursor object to execute SQL commands
        self.cursor = self.conn.cursor()

    def create_db(self):
        # Create a table named 'processed' with a column 'item_id'
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processed (
                item_id INTEGER PRIMARY KEY
            )
        """
        )

        # Create an index on the 'item_id' column
        self.cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_item_id ON processed (item_id)
        """
        )

        # Commit changes and close the connection
        self.conn.commit()

    def add_item_id_to_database(self, item_id: int):
        self.cursor.execute(
            """
            INSERT INTO processed (item_id) VALUES (?)
        """,
            (item_id,),
        )
        self.conn.commit()

    def get_count_of_done_item_ids(self):
        self.cursor.execute("SELECT COUNT(item_id) FROM processed")
        count = self.cursor.fetchone()[0]
        print(f"{count} item_ids found in the database")


wbi = WikibaseIntegrator(
    login=Login(user=config.user_name, password=config.bot_password)
)
scraper = EurlexScraper(wbi=wbi)
scraper.start()
