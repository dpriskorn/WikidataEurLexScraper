from models.title import Title


class TestTitle:
    def test_extract_eecid(self):
        ti = Title(language="en", value="Council Directive 88/610/EEC of 24 November 1988",
              celex_id="")
        assert ti.extract_eecid == "88/610/EEC"
