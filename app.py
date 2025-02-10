from parser import Parser
from loader import Loader
from ask import Ask
import pandas as pd
import pathlib
import streamlit as st
from st_keyup import st_keyup
import datetime
from datetime import timedelta
import os, yaml
from io import StringIO
import time
from streamlit_searchbox import st_searchbox
import uuid

st.title("My Expense")

with open("./config/config.yml", "r") as file:
    config = yaml.safe_load(file)

with st.form("filters"):
    # with st.sidebar:

    today = datetime.datetime.now()
    prev = today.month - 6

    # Date range picker with custom range
    three_months_ago = datetime.datetime.now() - timedelta(days=365)
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
    ["Upload statement", "Transactions", "Report", "Ask"]
)

p = Parser()
l = Loader()
a = Ask()


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

    # search_query = st.text_input("e.g. upi payments")

    search_query = st_searchbox(
        l.suggest, placeholder="e.g. upi zomato", key=5, default_use_searchterm=True
    )

    print(search_query)

    if not search_query:
        search_query = ""

    selected_categories = []
    selected_brands = []
    selected_others = []

    data = l.load(
        search=search_query,
        date_range=[start_date, end_date],
        categories=selected_categories,
        others=selected_others,
        brands=selected_brands,
    )

    with st.sidebar:

        st.title("Categories")
        for obj in data["aggregations"]["categories"]["buckets"]:
            if st.checkbox(
                str(obj["key"]) + " (" + str(obj["doc_count"]) + ")",
                # key=str(uuid.uuid4()),
            ):
                selected_categories.append(str(obj["key"]))

        st.title("Brands")
        for obj in data["aggregations"]["ner"]["buckets"]:
            if st.checkbox(
                str(obj["key"]) + " (" + str(obj["doc_count"]) + ")",
                # key=str(uuid.uuid4()),
            ):
                selected_brands.append(str(obj["key"]))

        st.title("Others")
        for obj in data["aggregations"]["other_filters"]["buckets"]:
            if st.checkbox(
                str(obj["key"]) + " (" + str(obj["doc_count"]) + ")",
                # key=str(uuid.uuid4()),
            ):
                selected_others.append(str(obj["key"]))

        if selected_categories or selected_others or selected_brands:

            data = l.load(
                search=search_query,
                date_range=[start_date, end_date],
                categories=selected_categories,
                others=selected_others,
                brands=selected_brands,
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

    expense_per_month = []
    expense_count = []
    expense_per_category = []

    reports_expense_pm = data["aggregations"]["expense_per_month"]["buckets"]
    reports_per_cateogry = data["aggregations"]["expense_per_category"]["buckets"]

    if reports_expense_pm:

        for pm in reports_expense_pm:
            expense_per_month.append(
                {"date": pm["key_as_string"], "amount": pm["expense_amount"]["value"]}
            )
            expense_count.append(
                {"date": pm["key_as_string"], "count": pm["doc_count"]}
            )

        st.title("Total Expense (Weekly)")
        st.line_chart(pd.DataFrame(expense_per_month).set_index("date"))

        st.title("Total Transactions (Weekly)")
        st.line_chart(pd.DataFrame(expense_count).set_index("date"))

    if reports_per_cateogry:

        for pc in reports_per_cateogry:

            expense_per_category.append(
                {"category": pc["key"], "amount": pc["total_expense"]["value"]}
            )

        st.bar_chart(pd.DataFrame(expense_per_category).set_index("category"))

with ask:

    st.header("Ask")

    messages = st.container(height=400)
    if prompt := st.chat_input("What was most expensive month?"):
        messages.chat_message("user").write(prompt)
        messages.chat_message("assistant").write(a.generator(prompt))
