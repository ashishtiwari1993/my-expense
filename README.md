# my-expense
Analyze your bank account statement and get insights.

## Create `config.yml`

```sh
cp config/sample.config.yml config/config.yml
```

Update all the credentials.

## Create ELSER inference 

```sh
PUT _inference/sparse_embedding/my-elser-model
{
  "service": "elasticsearch",
  "service_settings": {
    "adaptive_allocations": { 
      "enabled": true,
      "min_number_of_allocations": 1,
      "max_number_of_allocations": 4
    },
    "num_threads": 1,
    "model_id": ".elser_model_2_linux-x86_64" 
  }
}
```

## Create ingest pipeline

```sh
PUT my-expense
{
  "settings": {
    "index": {
      "analysis": {
        "analyzer": {
          "shingle_analyzer": {
            "type": "custom",
            "tokenizer": "standard",
            "filter": [
              "lowercase",
              "shingle_filter"
            ]
          }
        },
        "filter": {
          "shingle_filter": {
            "type": "shingle",
            "min_shingle_size": 2,
            "max_shingle_size": 3
          }
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "remarks_embedding": {
        "type": "sparse_vector"
      },
      "remarks": {
        "type": "text",
        "fields": {
          "suggest": {
            "type": "text",
            "analyzer": "shingle_analyzer"
          }
        }
      }
    }
  }
}
```

## Create an Index

```sh
PUT my-expense
{
  "mappings": {
    "properties": {
      "remarks_embedding": { 
        "type": "sparse_vector" 
      }
    }
  }
}
```

##  Sample search query

```sh
GET my-expense/_search
{
  "retriever": {
    "rrf": {
      "retrievers": [
        {
          "standard": {
            "query": {
              "bool": {
                "filter": [
                  {
                    "terms": {
                      "category.keyword": [
                        "medical"
                      ]
                    }
                  },
                  {
                    "range": {
                      "date": {
                        "gte": "2024-10-01",
                        "lte": "2024-12-31"
                      }
                    }
                  }
                ],
                "must": [
                  {
                    "match": {
                      "remarks": "dr amita"
                    }
                  }
                ]
              }
            }
          }
        },
        {
          "standard": {
            "query": {
              "bool": {
                "filter": [
                  {
                    "terms": {
                      "category.keyword": [
                        "medical"
                      ]
                    }
                  },
                  {
                    "range": {
                      "date": {
                        "gte": "2024-10-01",
                        "lte": "2024-12-31"
                      }
                    }
                  }
                ],
                "must": {
                  "sparse_vector": {
                    "inference_id": "my-elser-model",
                    "field": "remarks_embedding",
                    "query": "dr amita"
                  }
                }
              }
            }
          }
        }
      ],
      "rank_window_size": 50,
      "rank_constant": 20
    }
  },
  "aggs": {
    "categories": {
      "terms": {
        "field": "category.keyword"
      }
    },
    "other_filters": {
      "significant_text": {
        "field": "remarks",
        "size": 5
      }
    },
    "total_expense": {
      "sum": {
        "field": "transaction_amount"
      }
    },
    "ner": {
      "terms": {
        "field": "ner.entities.entity.keyword",
        "size": 5
      }
    }
  },
  "size": 30
}
```

## Install streamlit

```sh
pip install streamlit
pip install streamlit-searchbox
```

## Run

```sh
streamlit run app.py
```