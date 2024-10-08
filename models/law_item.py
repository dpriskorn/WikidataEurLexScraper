import logging
from typing import List, Set

import requests
from bs4 import BeautifulSoup, SoupStrainer
from pydantic import BaseModel
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.datatypes import URL, Time, MonolingualText
from wikibaseintegrator.entities import ItemEntity
from wikibaseintegrator.models import Reference, References, Claim
from wikibaseintegrator.wbi_enums import ActionIfExists

import config
from models.title import Title

logger = logging.getLogger(__name__)


class LawItem(BaseModel):
    edit_groups_hash: str  # mandatory
    something_to_upload: bool = False
    item: ItemEntity = None
    wbi: WikibaseIntegrator | None
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
    disabled_languages: Set[str] = set()

    class Config:
        arbitrary_types_allowed = True

    def get_disabled_languages(self) -> None:
        # get EN page
        url = (
            f"https://eur-lex.europa.eu/legal-content/EN"
            f"/TXT/?uri=CELEX:{self.celex_id}"
        )
        response = requests.get(url)

        # Use SoupStrainer to parse only the 'li' elements in the dropdown menu
        strainer = SoupStrainer("li")
        soup = BeautifulSoup(response.content, "lxml", parse_only=strainer)

        # Find all 'li' elements in the dropdown menu
        dropdown_items = soup.find_all("li", class_="disabled")

        # Extract language codes from each disabled element
        for item in dropdown_items:
            span = item.find("span")
            if span:
                lang_code = span.text.strip()
                if lang_code in self.languages:
                    self.disabled_languages.add(lang_code)

    def start(self):
        self.get_disabled_languages()
        self.scrape_law_titles()
        self.enrich_wikidata()

    def enrich_wikidata(self):
        self.item = self.wbi.item.get(entity_id=self.item_id)
        print(self.item.get_entity_url())
        self.add_labels_and_aliases()
        self.add_title_statements()
        if self.something_to_upload:
            # pprint(self.item.get_json())
            if config.press_enter_to_continue:
                input("press enter to upload")
            self.item.write(
                summary=f"Adding titles with [[Wikidata:Tools/WikidataEurLexScraper|WikidataEurLexScraper]] ([[:toolforge:editgroups/b/CB/{self.edit_groups_hash}|details]]) see [[Wikidata:Requests_for_permissions/Bot/So9qBot_8|bot_task]]"
            )
            print(self.item.get_entity_url())
            if config.press_enter_to_continue:
                input("press enter to continue")

    def title_claims(self) -> List[Claim]:
        return self.item.claims.get(property=config.title_property_id)

    @staticmethod
    def monotext_language(claim: Claim) -> str:
        # logger.debug(claim.mainsnak.datavalue)
        # we get lowercase from Wikibase
        return claim.mainsnak.datavalue["value"]["language"]

    @staticmethod
    def monotext_text(claim: Claim) -> str:
        # logger.debug(claim.mainsnak.datavalue)
        # we get lowercase from Wikibase
        return claim.mainsnak.datavalue["value"]["text"]

    def add_title_statements(self):
        print("Adding title-statements")
        claims = self.title_claims()
        for title in self.accepted_titles:
            logger.info(f"Working on title with lang '{title.language}'")
            # check if title claim already exists
            already_present = False
            for claim in claims:
                # logger.info()
                claim_lang = self.monotext_language(claim=claim)
                # logger.info(f"found title claim with lang: {claim_lang}")
                if (
                    claim_lang == title.language.lower()
                    and title.value == self.monotext_text(claim=claim)
                ):
                    logger.info(f"found title already present with lang: {claim_lang}")
                    already_present = True
            # print(already_present)
            if not already_present:
                logger.info(
                    f"no title with matching lang '{title.language}' found in item"
                )
                self.something_to_upload = True
                self.add_title_claim(title=title)

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
                        logger.info(f"title too long: '{title.value}'")
                    else:
                        title_for_this_language = title
            if title_for_this_language is not None:
                label = self.item.labels.get(language=language.lower())
                if label:
                    has_label = True
                    if label == title_for_this_language.value:
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
                                if alias == title_for_this_language.value:
                                    title_already_in_wikidata = True
                if not title_already_in_wikidata:  # and title_for_this_language.title
                    self.something_to_upload = True
                    # we are missing this data in Wikidata, lets add it
                    if not has_label:
                        # add as label
                        self.item.labels.set(
                            value=title_for_this_language.value, language=language_lower
                        )
                    else:
                        # add as alias
                        self.item.aliases.set(
                            values=[title_for_this_language.value],
                            language=language_lower,
                        )
                else:
                    logger.info("this title is already in Wikidata")

    def add_title_claim(self, title: Title):
        reference = Reference()
        reference.add(URL(prop_nr="P854", value=title.eurlex_url))  # reference URL
        reference.add(Time(prop_nr="P813", time="now"))  # retrieved
        references = References().add(reference)
        name_claim = MonolingualText(
            prop_nr=config.title_property_id,  # title
            language=title.language.lower(),
            text=title.value,
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
        available_languages = set(self.languages) - self.disabled_languages
        for language in available_languages:
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
                soup = BeautifulSoup(response.content, "lxml")

                # Find the element containing the law title using the provided jQuery selector
                law_title = soup.select_one("p#title").get_text(strip=True)
                # Guard against None
                if law_title and law_title is not None:
                    title = Title(
                        value=law_title, language=language, celex_id=self.celex_id
                    )
                    self.accepted_titles.append(title)
                else:
                    raise ValueError(f"no law title found, see {url}")
            else:
                logger.info(f"got {response.status_code} from eur-lex")
