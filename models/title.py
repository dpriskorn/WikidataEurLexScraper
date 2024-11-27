import logging
import re
from re import Pattern
from typing import Dict, Set

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Title(BaseModel):
    value: str
    language: str
    celex_id: str
    eecid_pattern: Pattern = re.compile(r"(\d{2}\/\d{1,4}\/[A-ZØ]{3,4})")
    # This dict was written by Samoasambia, see https://github.com/Samoasambia/wikidata/blob/main/EU%20legal%20act%20short%20title.ipynb
    regex_list: Dict[str,str] = {
        "bg": r"(^(Делегиран )?(Регламент|Директива|Решение|Препоръка)( за изпълнение)? \([^)]+\) \d{4}/\d+(?P<i> на Европейския парламент и на Съвета| на Съвета| на Комисията))",
        "cs": r"(^(Prováděcí )?(Nařízení|Směrnice|Rozhodnutí|Doporučení)(?P<i> Rady| Komise)?( v přenesené pravomoci)? \([^)]+\) \d{4}/\d+(?P<i2> Evropského parlamentu a Rady)?)",
        "da": r"(^(?P<i>Europa-Parlamentets og Rådets |Rådets |Kommissionens )(delegerede |gennemførelses)?(forordning|direktiv|afgørelse|henstilling) \([^)]+\) \d{4}/\d+)",
        "de": r"(^(Delegierte |Durchführungs)?(Verordnung|Richtlinie|Beschluss|Empfehlung) \([^)]+\) \d{4}/\d+(?P<i> des Europäischen Parlaments und des Rates| des Rates| der Kommission))",
        "el": r"(^(Κατ' εξουσιοδότηση |Εκτελεστικός |Εκτελεστική)?(Κανονισμός|Οδηγία|Απόφαση|Σύσταση) \([^)]+\) \d{4}/\d+(?P<i> του Ευρωπαϊκού Κοινοβουλίου και του Συμβουλίου| του Συμβουλίου| της Επιτροπής))",
        "en": r"(^(?P<i>Council |Commission )?(Delegated |Implementing )?(Regulation|Directive|Decision|Recommendation) \([^)]+\) \d{4}/\d+(?P<i2> of the European Parliament and of the Council)?)",
        "es": r"(^(Reglamento|Directiva|Decisión|Recomendación)( Delegado| de Ejecución)? \([^)]+\) \d{4}/\d+(?P<i> del Parlamento Europeo y del Consejo| del Consejo| de la Comisión))",
        "et": r"(^(?P<i>Euroopa Parlamendi ja nõukogu |Nõukogu |Komisjoni )(delegeeritud |rakendus)?(määrus|direktiiv|otsus|soovitus) \([^)]+\) \d{4}/\d+)",
        "fi": r"(^(?P<i>Euroopan parlamentin ja neuvoston |Neuvoston |Komission )(delegoitu |täytäntöönpano)?(asetus|direktiivi|päätös|suositus) \([^)]+\) \d{4}/\d+)",
        "fr": r"(^(Règlement|Directive|Décision|Recommandation)( délégué| d'exécution)? \([^)]+\) \d{4}/\d+(?P<i> du Parlement européen et du Conseil| du Conseil| de la Commission))",
        "ga": r"(^(Rialachán|Treoir|Cinneadh|Molta)( Tarmligthe| Cur Chun Feidhme)?(?P<i> ón gComhairle| ón gCoimisiún)? \([^)]+\) \d{4}/\d+(?P<i2> ó Pharlaimint na hEorpa agus ón gComhairle| ón gComhairle| ón gCoimisiún)?)",
        "hr": r"(^(Delegirana |Provedbena )?(Uredba|Direktiva|Odluka|Preporuka)(?P<i> Vijeća| Komisije)? \([^)]+\) \d{4}/\d+(?P<i2> Europskog parlamenta i Vijeća)?)",
        "hu": r"(^(?P<i>Az Európai Parlament és a Tanács |A Tanács |A Bizottság )\([^)]+\) \d{4}/\d+ (felhatalmazáson alapuló |végrehajtási )?(rendelete|irányelve|határozata|ajánlása))",
        "it": r"(^(Regolamento|Direttiva|Decisione|Raccomandazione)( delegato| di esecuzione)? \([^)]+\) \d{4}/\d+(?P<i> del Parlamento europeo e del Consiglio| del Consiglio| della Commissione))",
        "lt": r"^\d{4} m\. \w+ \d{1,2} d\. ((?P<i>Europos Parlamento ir Tarybos |Tarybos |Komisijos )(deleguotasis |įgyvendinimo )?(reglamentas|direktyva|sprendimas|rekomendacija) \([^)]+\) \d{4}/\d+)",
        "lv": r"(^(?P<i>Eiropas Parlamenta un Padomes |Padomes |Komisijas )(Deleģētā |Īstenošanas )?(Regula|Direktīva|lēmums|Ieteikums) \([^)]+\) \d{4}/\d+)",
        "mt": r"(^(Regolament|Direttiva|Deċiżjoni|Rakkomandazzjoni)( delegat| ta' Implimentazzjoni)?(?P<i> tal-Kunsill| tal-Kummissjoni)? \([^)]+\) \d{4}/\d+(?P<i2> tal-Parlament Ewropew u tal-Kunsill)?)",
        "nl": r"(^(Gedelegeerde |Uitvoerings)?(Verordening|Richtlijn|Besluit|Aanbeveling) \([^)]+\) \d{4}/\d+(?P<i> van het Europees Parlement en de Raad| van de Raad| van de Commissie))",
        "pl": r"(^(Rozporządzenie|Dyrektywa|Decyzja|Zalecenie)( delegowan(e|a)| wykonawcz(e|a))? (?P<i>Parlamentu Europejskiego i Rady |Rady |Komisji )\([^)]+\) \d{4}/\d+)",
        "pt": r"(^(Regulamento|Diretiva|Decisão|Recomendação)( Delegado| de Execução)? \([^)]+\) \d{4}/\d+(?P<i> do Parlamento Europeu e do Conselho| do Conselho| da Comissão))",
        "ro": r"(^(Regulamentul|Directiva|Decizia|Recomandarea)( delegat| de punere în aplicare)? \([^)]+\) \d{4}/\d+(?P<i> (a|al) Parlamentului European și (a|al) Consiliului| (a|al) Consiliului| (a|al) Comisiei))",
        "sk": r"(^(Delegované |Vykonávacie )?(Nariadenie|Smernica|Rozhodnutie|Odporúčanie) (?P<i>Európskeho parlamentu a Rady |Rady |Komisie )\([^)]+\) \d{4}/\d+)",
        "sl": r"(^(Delegirana |Delegirani |Izvedbena |Izvedbeni )?(Uredba|Direktiva|Sklep|Priporočilo)(?P<i> Sveta| Komisije)? \([^)]+\) \d{4}/\d+(?P<i2> Evropskega parlamenta in Sveta)?)",
        "sv": r"(^(?P<i>Europaparlamentets och rådets |Rådets |Kommissionens )(delegerade |genomförande)?(förordning|direktiv|beslut|rekommendation) \([^)]+\) \d{4}/\d+)",
    }
    # checks capitalization for certain languages before returning
    lowercase_lang: Set[str] = {"cs", "da", "el", "et", "fi", "fr", "it", "hu", "pl", "sk", "sv"}

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

    @staticmethod
    def uppercase_initial(text) -> str:
        """This function was written by Samoasambia, see https://github.com/Samoasambia/wikidata/blob/main/EU%20legal%20act%20short%20title.ipynb"""
        return text[0].upper() + text[1:]

    @staticmethod
    def lowercase_initial(text) -> str:
        """This function was written by Samoasambia, see https://github.com/Samoasambia/wikidata/blob/main/EU%20legal%20act%20short%20title.ipynb"""
        return text[0].lower() + text[1:]

    @property
    def shortname_with_institution(self) -> str:
        # get the right regex for the given language
        regex = self.regex_list.get(self.language)
        # if not regex:
        # raise ValueError(f"Unknown language: {lang}")

        # matching with the regex
        match = re.search(regex, self.value, re.IGNORECASE)
        if match:
            return match.group(1)
        else:
            return ""

    @property
    def shortname_without_institution(self) -> str:
        """This function was written by Samoasambia, see https://github.com/Samoasambia/wikidata/blob/main/EU%20legal%20act%20short%20title.ipynb"""
        # BUG: IGNORECASE doesn't work in Greek
        # if self.language == "el":
        #     return self.value
        # get the right regex for the given language
        regex = self.regex_list.get(self.language)

        # matching with the regex
        match = re.search(regex, self.value, re.IGNORECASE)

        if match:
            shortname = match.group(1)

            # removes regex group "i"
            if "i" in match.groupdict() and match.group("i") is not None:
                substract = match.group("i")
                shortname = re.sub(substract, "", shortname)

            # removes regex group "i2"
            if "i2" in match.groupdict() and match.group("i2") is not None:
                substract = match.group("i2")
                shortname = re.sub(substract, "", shortname)

            if self.language in self.lowercase_lang:
                return self.lowercase_initial(shortname)
            else:
                return self.uppercase_initial(shortname)
