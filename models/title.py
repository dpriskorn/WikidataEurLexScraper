import logging
import re
from re import Pattern

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Title(BaseModel):
    value: str
    language: str
    celex_id: str
    eecid_pattern: Pattern = re.compile(r"(\d{2}\/\d{1,4}\/[A-ZØ]{3,4})")

    @property
    def eurlex_url(self):
        return (
            f"https://eur-lex.europa.eu/legal-content/{self.language}"
            f"/TXT/?uri=CELEX:{self.celex_id}"
        )

    @property
    def longer_than_wikidata_support(self) -> bool:
        return bool(len(self.value) > 250)

    @property
    def extract_eecid(self) -> str:
        """This looks like this 88/610/EEC and the last part is localized."""
        match = re.search(self.eecid_pattern, self.value)
        if match:
            return match.group(0)
        else:
            return ""
