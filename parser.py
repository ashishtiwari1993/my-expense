import re
import yaml
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import ChatOllama


class Parser:

    def __init__(self):

        with open("./config/config.yml", "r") as file:
            c = yaml.safe_load(file)
            self._config = c

        self.llm = ChatOllama(
            base_url=c["ollama"]["base_url"],
            model=c["ollama"]["model"],
            temperature=0,
        )

        self.es = Elasticsearch(
            cloud_id=c["elastic"]["cloud_id"], api_key=c["elastic"]["api_key"]
        )

    def starts_with_date_format(self, s):
        # Define the date format regex: 2 digits, a 3-letter month, and 4-digit year
        date_pattern = r"^\d{2} \w{3}, \d{4}"
        return bool(re.match(date_pattern, s))

    def parse_transaction(self, transaction_str):
        # Define a regular expression to extract the required components
        pattern = re.compile(
            r"(?P<date>\d{2} \w{3}, \d{4})\s+"  # Date
            r"(?P<details>.+?)\s+"  # Transaction details
            r"(?P<amount>-?[0-9,]+\.\d{2})\s+"  # Transaction amount
            r"(?P<balance>[0-9,]+\.\d{2})"  # Balance
        )

        # Match the pattern
        match = pattern.match(transaction_str)

        if match:
            # Extract groups
            date = match.group("date")
            details = match.group("details")
            amount = float(match.group("amount").replace(",", ""))
            balance = float(match.group("balance").replace(",", ""))
            transaction_type = "debit" if amount < 0 else "credit"

            # Construct the result
            result = {
                "date": self.format_date(date),
                "remarks": details,
                "transaction_type": transaction_type,
                "transaction_amount": abs(amount),
                "balance": balance,
            }

            return result
        else:
            return False

    def format_date(self, date_str):

        cleaned_date_str = (
            date_str.replace("st", "")
            .replace("nd", "")
            .replace("rd", "")
            .replace("th", "")
        )
        date_obj = datetime.strptime(cleaned_date_str, "%d %b, %Y")
        formatted_date = date_obj.strftime("%Y-%m-%d")
        return formatted_date

    def generate_category(self, remarks):
        result = self.llm.invoke(
            "Just return one word lower case transaction category for bank transaction remarks from given category only (shopping, food, ride, medical, hotel, entertainment, transfer, card_payment, unknown) or else return 'unknown' if not able to detect -"
            + remarks
        )
        return result.content

    def parse(self, statement="", password=""):

        file_path = statement

        loader = PyPDFLoader(file_path=file_path, password=password)
        pages = []

        for page in loader.load():
            pages.append(page)

            if (
                "DATE TRANSACTION DETAILS CHEQUE/REFERENCE# DEBIT  CREDIT  BALANCE"
                in page.page_content
            ):
                p = page.page_content.split(
                    "DATE TRANSACTION DETAILS CHEQUE/REFERENCE# DEBIT  CREDIT  BALANCE"
                )

                for t in p:
                    txn = t.split("\n")

                    if len(txn) > 2:
                        for transaction in txn:
                            if self.starts_with_date_format(transaction):
                                j = self.parse_transaction(transaction)

                                if j:
                                    category = self.generate_category(j["remarks"])
                                    j.update({"category": category})
                                    yield j

    def run(self, statement="", password=""):

        bulk(
            client=self.es,
            index=self._config["elastic"]["index_name"],
            pipeline="elser-embedding-pipeline",
            actions=self.parse(statement=statement, password=password),
        )
