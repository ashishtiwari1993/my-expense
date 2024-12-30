from parser import Parser
from loader import Loader
import pandas as pd
import pathlib
import streamlit as st
from st_keyup import st_keyup
import datetime
from datetime import timedelta
import os, yaml
from io import StringIO

with open("./config/config.yml", "r") as file:
    config = yaml.safe_load(file)

with st.form("filters"):
    with st.sidebar:

        today = datetime.datetime.now()
        prev = today.month - 3

        # Date range picker with custom range
        three_months_ago = datetime.datetime.now() - timedelta(days=90)
        min_date = datetime.datetime.now() - timedelta(days=3 * 365)
        max_date = datetime.datetime.now() + timedelta(days=3 * 365)

        date_range = st.date_input(
            "Select Date Range:",
            value=(three_months_ago.date(), datetime.datetime.now().date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
            format="YYYY.MM.DD",
        )

        start_date = date_range[0].strftime("%Y-%m-%d")
        end_date = date_range[1].strftime("%Y-%m-%d")

        submit = st.form_submit_button("Submit")


statement_dir = str(pathlib.Path().resolve()) + "/statements/"

upload, txn, summary, ask = st.tabs(
    ["Upload statement", "Transactions", "Summary report", "Ask"]
)

p = Parser()
l = Loader()


with upload:

    st.header("Upload PDF account statement")

    uploaded_file = st.file_uploader("Upload PDF")

    if uploaded_file is not None:

        with st.spinner("Parsing ..."):
            save_path = os.path.join(statement_dir, uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            p.run(
                statement=statement_dir + uploaded_file.name,
                password=config["pdf"]["password"],
            )

        st.success("Parsing complete!")


with txn:

    st.header("Transactions")

    search_query = st_keyup("Search")

    selected_categories = []
    selected_others = []

    data = l.load(
        search=search_query,
        date_range=[start_date, end_date],
        categories=selected_categories,
        others=selected_others,
    )

    with st.sidebar:

        st.title("Categories")
        for obj in data["aggregations"]["categories"]["buckets"]:
            if st.checkbox(str(obj["key"]) + " (" + str(obj["doc_count"]) + ")"):
                selected_categories.append(str(obj["key"]))

        st.title("Others")
        for obj in data["aggregations"]["other_filters"]["buckets"]:
            if st.checkbox(str(obj["key"]) + " (" + str(obj["doc_count"]) + ")"):
                selected_others.append(str(obj["key"]))

    data = l.load(
        search=search_query,
        date_range=[start_date, end_date],
        categories=selected_categories,
        others=selected_others,
    )

    text = "Found:" + str(data["hits"]["total"]["value"])
    total_expense_text = "Expense INR ~ " + str(
        round(data["aggregations"]["total_expense"]["value"], 2)
    )

    st.text(text)
    st.text(total_expense_text)

    df = pd.DataFrame(pd.json_normalize(data["hits"]["hits"]))
    st.table(df.iloc[:, -4:])

with summary:
    st.header("Summary")
    st.image("https://static.streamlit.io/examples/dog.jpg")
with ask:
    st.header("ask")
    st.image("https://static.streamlit.io/examples/owl.jpg")
