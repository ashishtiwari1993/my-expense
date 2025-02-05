# my-expense
Analyze your bank account statement and get insights.

## Create `config.yml`

```sh
cp config/sample.config.yml config/config.yml
```

Update all the credentials.

## Create Elser inference 

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
PUT _ingest/pipeline/my-expense-pipeline
{
  "processors": [
    {
      "inference": {
        "model_id": "my-elser-model",
        "input_output": [
          {
            "input_field": "remarks",
            "output_field": "remarks_embedding"
          }
        ]
      }
    },
    {
      "inference": {
        "model_id": "elastic__distilbert-base-uncased-finetuned-conll03-english",
        "target_field": "ner",
        "field_map": {
          "remarks": "text_field"
        }
      }
    }
  ]
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
