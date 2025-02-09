from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import yaml


class Loader:

    def __init__(self):

        with open("./config/config.yml", "r") as file:
            c = yaml.safe_load(file)
            self._config = c

        self.es = Elasticsearch(
            cloud_id=c["elastic"]["cloud_id"], api_key=c["elastic"]["api_key"]
        )

    def suggest(self, search=""):

        body = {
            "suggest": {
                "text": search,
                "simple_phrase": {
                    "phrase": {
                        "field": "remarks.suggest",
                        "size": 5,
                        "gram_size": 3,
                        "direct_generator": [
                            {"field": "remarks.suggest", "suggest_mode": "always"}
                        ],
                    }
                },
            }
        }

        resp = self.es.search(
            index=self._config["elastic"]["index_name"],
            body=body,
        )

        suggestions = []

        for phrase in resp["suggest"]["simple_phrase"]:
            if phrase["options"]:
                for s in phrase["options"]:
                    suggestions.append(s["text"])

        return suggestions

    def load(self, search="", date_range=[], categories=[], others=[], brands=[]):

        filter = []
        must = []

        if search:
            search_query = {"match": {"remarks": search}}

            must.append(search_query)

        if others:
            others_query = {"match": {"remarks": ",".join(others)}}

            filter.append(others_query)

        if categories:
            category_search = {"terms": {"category.keyword": categories}}

            filter.append(category_search)

        if brands:

            brand_search = {"terms": {"ner.entities.entity.keyword": brands}}

            filter.append(brand_search)

        date = {"range": {"date": {"gte": date_range[0], "lte": date_range[1]}}}

        filter.append(date)

        q = {"standard": {"query": {"bool": {"filter": filter, "must": must}}}}

        elser = {
            "standard": {
                "query": {
                    "bool": {
                        "filter": filter,
                        "must": {
                            "sparse_vector": {
                                "inference_id": "my-elser-model",
                                "field": "remarks_embedding",
                                "query": search,
                            }
                        },
                    }
                }
            }
        }

        aggs = {
            "categories": {"terms": {"field": "category.keyword"}},
            "other_filters": {"significant_text": {"field": "remarks", "size": 5}},
            "total_expense": {"sum": {"field": "transaction_amount"}},
            "ner": {"terms": {"field": "ner.entities.entity.keyword", "size": 5}},
            "expense_per_month": {
                "date_histogram": {
                    "field": "date",
                    "calendar_interval": "week",
                    "format": "yyyy-MM-dd",
                },
                "aggs": {"expense_amount": {"sum": {"field": "transaction_amount"}}},
            },
            "expense_per_category": {
                "terms": {"field": "category.keyword"},
                "aggs": {"total_expense": {"sum": {"field": "transaction_amount"}}},
            },
        }

        final_query = {
            "retriever": {
                "rrf": {
                    "retrievers": [q, elser],
                    "rank_window_size": 70,
                    "rank_constant": 20,
                },
            },
            "aggs": aggs,
            "size": 50,
        }

        print(final_query)

        resp = self.es.search(
            index=self._config["elastic"]["index_name"],
            source_includes=["date", "category", "remarks", "transaction_amount"],
            body=final_query,
        )
        return resp
