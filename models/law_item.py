import logging
from pprint import pprint
from typing import List

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.datatypes import URL, Time, MonolingualText
from wikibaseintegrator.entities import ItemEntity
from wikibaseintegrator.models import Reference, References
from wikibaseintegrator.wbi_enums import ActionIfExists

import config
from models.title import Title

logger = logging.getLogger(__name__)

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
            # pprint(self.item.get_json())
            if config.press_enter_to_continue:
                input("press enter to upload")
            self.item.write(
                summary="Adding names with [[Wikidata:Tools/WikidataEurLexScraper|WikidataEurLexScraper]]"
            )
            print(self.item.get_entity_url())
            if config.press_enter_to_continue:
                input("press enter to continue")

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
        reference = Reference()
        reference.add(URL(prop_nr="P854", value=title.eurlex_url))  # reference URL
        reference.add(Time(prop_nr="P813", time="now"))  # retrieved
        references = References().add(reference)
        name_claim = MonolingualText(
            prop_nr="P1448",  # official name
            language=title.language.lower(),
            text=title.title,
            references=references,
        )
        # pprint(name_claim.get_json())
        # exit()
        self.item.claims.add(
            claims=[name_claim],
            action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND,
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
