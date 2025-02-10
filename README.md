# my-expense
Analyze your bank account statement and get insights.

## Install dependencies

```sh
pip install -r requirements.txt
```

## Install streamlit

```sh
pip install streamlit
pip install streamlit-searchbox
```

## Setup Ollama

1. [Install](https://ollama.com/download) Ollama
2. Run Llama 3.1
```sh
ollama run llama3.1
```

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
    },
    {
      "script": {
        "lang": "painless",
        "source": """
        if (ctx.containsKey("remarks")) {
          if (ctx.remarks.toLowerCase().contains("imps")) {
            ctx.category = "transfer";
          }        
          if (ctx.remarks.toLowerCase().contains("zomato") || ctx.remarks.toLowerCase().contains("swiggy")) {
            ctx.category = "food";
          }
          if (ctx.remarks.toLowerCase().contains("blinkit") || ctx.remarks.toLowerCase().contains("amazon") || ctx.remarks.toLowerCase().contains("flipkart")) {
            ctx.category = "shopping";
          }
          if (ctx.remarks.toLowerCase().contains("bharti multispe")) {
            ctx.category = "medical";
          }
          if (ctx.remarks.toLowerCase().contains("cred")) {
            ctx.category = "card_payment";
          }
          if (ctx.remarks.toLowerCase().contains("bookmyshow") || ctx.remarks.toLowerCase().contains("airtel")) {
            ctx.category = "entertainment";
          }
          if (ctx.remarks.toLowerCase().contains("savaari")) {
            ctx.category = "ride";
          }
        }  
        """
      }
    }
  ]
}
```

## Create an Index

```sh
PUT my-expense
{
  "settings": {
    "index": {
      "analysis": {
        "analyzer": {
          "suggest_analyzer": {
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
            "analyzer": "suggest_analyzer"
          }
        }
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
                    "range": {
                      "date": {
                        "gte": "2024-02-10",
                        "lte": "2025-02-09"
                      }
                    }
                  }
                ],
                "must": [
                  {
                    "match": {
                      "remarks": "coffee expense"
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
                    "range": {
                      "date": {
                        "gte": "2024-02-10",
                        "lte": "2025-02-09"
                      }
                    }
                  }
                ],
                "must": {
                  "sparse_vector": {
                    "inference_id": "my-elser-model",
                    "field": "remarks_embedding",
                    "query": "coffee expense"
                  }
                }
              }
            }
          }
        }
      ],
      "rank_window_size": 70,
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
    },
    "expense_per_month": {
      "date_histogram": {
        "field": "date",
        "calendar_interval": "week",
        "format": "yyyy-MM-dd"
      },
      "aggs": {
        "expense_amount": {
          "sum": {
            "field": "transaction_amount"
          }
        }
      }
    },
    "expense_per_category": {
      "terms": {
        "field": "category.keyword"
      },
      "aggs": {
        "total_expense": {
          "sum": {
            "field": "transaction_amount"
          }
        }
      }
    }
  },
  "size": 50
}
```


## Create `config.yml`

```sh
cp config/sample.config.yml config/config.yml
```

Update all the credentials.

## Run

```sh
streamlit run app.py
```
