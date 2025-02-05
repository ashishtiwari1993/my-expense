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

        # print("search received -" + search)

        # q = {
        #     "size": 30,
        #     "query": {
        #         "bool": {
        #             "must": [],
        #             "filter": [
        #                 {
        #                     "range": {
        #                         "date": {"gte": date_range[0], "lte": date_range[1]}
        #                     }
        #                 }
        #             ],
        #         }
        #     },
        #     "aggs": {
        #         "categories": {"terms": {"field": "category.keyword"}},
        #         "other_filters": {"significant_text": {"field": "remarks"}},
        #         "total_expense": {"sum": {"field": "transaction_amount"}},
        #     },
        # }

        must = []

        if search:
            search_query = {"match": {"remarks": search}}

            must.append(search_query)

        if others:
            search_query = {"match": {"remarks": ",".join(others)}}

            must.append(search_query)

        if categories:
            category_search = {"terms": {"category.keyword": categories}}

            must.append(category_search)

        q = {
            "standard": {
                "query": {
                    "bool": {
                        "must": must,
                        "filter": [
                            {
                                "range": {
                                    "date": {"gte": date_range[0], "lte": date_range[1]}
                                }
                            }
                        ],
                    }
                }
            }
        }

        elser = {
            "standard": {
                "query": {
                    "sparse_vector": {
                        "inference_id": "my-elser-model",
                        "field": "remarks_embedding",
                        "query": search,
                    }
                }
            }
        }

        aggs = {
            "categories": {"terms": {"field": "category.keyword"}},
            "other_filters": {"significant_text": {"field": "remarks"}},
            "total_expense": {"sum": {"field": "transaction_amount"}},
        }

        final_query = {
            "retriever": {
                "rrf": {
                    "retrievers": [q, elser],
                    "rank_window_size": 50,
                    "rank_constant": 20,
                },
            },
            "aggs": aggs,
            "size": 30,
        }

        print(final_query)

        resp = self.es.search(
            index=self._config["elastic"]["index_name"],
            source_includes=["date", "category", "remarks", "transaction_amount"],
            body=final_query,
        )
        return resp

    def reports(self, date_range=[]):

        q = {
            "size": 0,
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
                "expense_per_month": {
                    "date_histogram": {
                        "field": "date",
                        "calendar_interval": "week",
                        "format": "yyyy-MM-dd",
                    },
                    "aggs": {
                        "expense_amount": {"sum": {"field": "transaction_amount"}}
                    },
                },
                "expense_per_category": {
                    "terms": {"field": "category.keyword"},
                    "aggs": {"total_expense": {"sum": {"field": "transaction_amount"}}},
                },
            },
        }

        resp = self.es.search(index=self._config["elastic"]["index_name"], body=q)

        return resp
