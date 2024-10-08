import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Title(BaseModel):
    value: str
    language: str
    celex_id: str
    # detected_language: str = ""
    # score: float = 0.0

    @property
    def eurlex_url(self):
        return (
            f"https://eur-lex.europa.eu/legal-content/{self.language}"
            f"/TXT/?uri=CELEX:{self.celex_id}"
        )

    @property
    def longer_than_wikidata_support(self) -> bool:
        return bool(len(self.value) > 250)

    # def detect_language(self) -> None:
    #     # This returns a dict like so: {'lang': 'tr', 'score': 0.9982126951217651}
    #     language_result = detect(text=self.title, low_memory=False)
    #     self.detected_language = language_result["lang"]
    #     self.score = language_result["score"]
    #     if self.accepted_title:
    #         logger.info(f"got good title for language {self.detected_language}")
    #     else:
    #         if self.languages_match:
    #             logger.info(
    #                 f"got title we do not accept because of low score of {self.score} for {self.detected_language}"
    #             )
    #         else:
    #             logger.info(
    #                 f"Eur-Lex language {self.language} and detected language {self.detected_language} did not match"
    #             )
    #             logger.debug(f"for title {self.title} with score: {self.score}")

    # @property
    # def languages_match(self) -> bool:
    #     return bool(self.language.lower() == self.detected_language)

    # @property
    # def accepted_title(self) -> bool:
    #     """We accept scores over 0.4 for all languages"""
    #     if self.languages_match:
    #         if self.score > 0.4:
    #             return True
    #     return False
