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

    def load(self, search="", date_range=[], categories=[], others=[]):

        print("search received -" + search)

        q = {
            "size": 30,
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "range": {
                                "date": {"gte": date_range[0], "lte": date_range[1]}
                            }
                        }
                    ],
                }
            },
            "aggs": {
                "categories": {"terms": {"field": "category.keyword"}},
                "other_filters": {"significant_text": {"field": "remarks"}},
                "total_expense": {"sum": {"field": "transaction_amount"}},
            },
        }

        if search:
            search_query = {"match": {"remarks": search}}

            q["query"]["bool"]["must"].append(search_query)

        if others:
            search_query = {"match": {"remarks": ",".join(others)}}

            q["query"]["bool"]["must"].append(search_query)

        if categories:
            category_search = {"terms": {"category.keyword": categories}}

            q["query"]["bool"]["must"].append(category_search)

        resp = self.es.search(
            index="my-expense",
            source_includes=["date", "category", "remarks", "transaction_amount"],
            body=q,
        )
        return resp
