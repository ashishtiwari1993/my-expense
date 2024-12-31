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

    if selected_categories or selected_others:

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

    reports = l.reports(date_range=[start_date, end_date])

    expense_per_month = []
    expense_count = []
    expense_per_category = []

    reports_expense_pm = reports["aggregations"]["expense_per_month"]["buckets"]
    reports_expense_pc = reports["aggregations"]["expense_per_category"]["buckets"]

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

with ask:

    st.header("ask")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            response = st.write_stream(a.generator(prompt))
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
