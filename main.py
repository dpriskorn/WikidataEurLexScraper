"""This is a tool for scraping information from Eur-Lex
https://www.wikidata.org/wiki/Property:P476 is the CELEX property
query https://query.wikidata.org/#SELECT%20%28COUNT%28%3Fitem%29%20AS%20%3Fcount%29%0AWHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP476%20%3Fvalue.%0A%7D%0A
There are 4594 items with this identifier right now.
It currently only scrapes the name of the law"""
import logging
import sqlite3
from typing import List, Any

from pydantic import BaseModel
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbconfig
from wikibaseintegrator.wbi_helpers import execute_sparql_query
from wikibaseintegrator.wbi_login import Login

import config
from models.law_item import LawItem

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)
wbconfig["USER_AGENT"] = config.user_agent


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
    max: int = 0

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
        count = 0
        for item in self.items:
            if count >= self.max:
                print("Reached max number of items to work on. Stopping")
                break
            else:
                item_id = int(item.item_id[1:])
                if not self.already_processed(item_id=item_id):
                    item.start()
                    self.add_item_id_to_database(item_id=item_id)
                    count += 1
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
scraper = EurlexScraper(wbi=wbi, max=1)
scraper.start()
