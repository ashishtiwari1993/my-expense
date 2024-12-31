from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from langchain_community.tools import TavilySearchResults
import yaml, json, os
import time
from openai import OpenAI


class Ask:

    def __init__(self):

        with open("./config/config.yml", "r") as file:
            c = yaml.safe_load(file)
            self._config = c

        self.es = Elasticsearch(
            cloud_id=c["elastic"]["cloud_id"], api_key=c["elastic"]["api_key"]
        )

        self.open_ai_client = OpenAI(
            api_key=c["open_ai"]["api_key"],
        )

        os.environ["TAVILY_API_KEY"] = c["tavily"]["api_key"]

    def build_query(self, query=""):

        mapping = self.es.indices.get_mapping(
            index=self._config["elastic"]["index_name"]
        )
        sample_doc = self.es.search(index=self._config["elastic"]["index_name"], size=1)

        few_shots_prompt = """
            1.  User Query = what was the november month 2024 total expense
                Elasticsearch query DSL = {
                    "size": 0,
                    "query": {
                        "bool": {
                        "must": [
                            {
                            "match": {
                                "transaction_type": "debit"
                            }
                            },
                            {
                            "range": {
                                "date": {
                                "gte": "2024-11-01",
                                "lte": "2024-11-30"
                                }
                            }
                            }
                        ]
                        }
                    },
                    "aggs": {
                        "total_expense": {
                        "sum": {
                            "field": "transaction_amount"
                        }
                        }
                    }
                }

            2. Query - Where I spend a lot of money


        """

        prompt = f"""
            Use below index mapping and reference document to build Elasticsearch query:

            Index mapping:
            {mapping}

            Reference elasticsearch document:
            {sample_doc}

            Return single line Elasticsearch Query DSL according to index mapping for the below search query related to transactions/expense.:

            {query}

            Just return Query DSL without REST specification (e.g. GET, POST etc.) and json markdown format (e.g. ```json)
        """

        resp = self.open_ai_client.chat.completions.create(
            model=self._config["open_ai"]["model"],
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0,
        )

        return resp.choices[0].message.content

    def fetch_from_elasticsearch(self, query=""):

        query_dsl = self.build_query(query)

        resp = self.es.search(
            index=self._config["elastic"]["index_name"], body=query_dsl
        )
        return resp

    def general_enquiry(self, query=""):

        web_search = TavilySearchResults(max_results=5)
        resp = web_search.invoke({"query": query})
        return resp

    def run(self, query=""):

        all_functions = [
            {
                "type": "function",
                "function": {
                    "name": "fetch_from_elasticsearch",
                    "description": "All trasactions related data is stored into Elasticsearch in INR. Call this function if receiving any query around transactions like expense, expenses category etc. .",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Exact query string which is asked by user.",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "general_enquiry",
                    "description": "Route all other general enquiries / queries here for the web search.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Exact query string which is asked by user.",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

        messages = []
        messages.append(
            {
                "role": "system",
                "content": "If no data received from any function. Just say there is issue fetching details from function(function_name).",
            }
        )

        messages.append(
            {
                "role": "user",
                "content": query,
            }
        )

        response = self.open_ai_client.chat.completions.create(
            model=self._config["open_ai"]["model"],
            messages=messages,
            tools=all_functions,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:

            available_functions = {
                "fetch_from_elasticsearch": self.fetch_from_elasticsearch,
                "general_enquiry": self.general_enquiry,
            }
            messages.append(response_message)

            for tool_call in tool_calls:

                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)

                if function_name == "fetch_from_elasticsearch":
                    function_response = function_to_call(
                        query=function_args.get("query"),
                    )

                if function_name == "general_enquiry":
                    function_response = function_to_call(
                        query=function_args.get("query"),
                    )

                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(function_response),
                    }
                )

        second_response = self.open_ai_client.chat.completions.create(
            model=self._config["open_ai"]["model"],
            messages=messages,
        )

        return second_response.choices[0].message.content

    def generator(self, query=""):
        response = self.run(query=query)
        for word in response.split():
            yield word + " "
            time.sleep(0.05)
