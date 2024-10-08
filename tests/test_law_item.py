from unittest import TestCase

from models.law_item import LawItem


class TestLawItem(TestCase):
    def test_get_disabled_languages(self):
        li = LawItem(celex_id="31988L0406", item_id="", wbi=None)
        li.get_disabled_languages()
        assert li.disabled_languages == {
            "ET",
            "CS",
            "HR",
            "BG",
            "HU",
            "LT",
            "RO",
            "SK",
            "MT",
            "GA",
            "PL",
            "SL",
            "LV",
        }
