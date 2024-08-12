import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAI
import ast

# Initialize session state variables if they do not exist
if 'have_data' not in st.session_state:
    st.session_state.have_data = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if 'date_conversion' not in st.session_state:
    st.session_state.date_conversion = False
if 'file_name' not in st.session_state:
    st.session_state.file_name = None

# Create a connection engine to SQLite database
if 'engine' not in st.session_state:
    st.session_state.engine = create_engine('sqlite:///data.db', echo=False)

# Fetch OpenAI API key from Streamlit secrets
openai_api_key = st.secrets["openai"]["api_key"]


def load_csv_to_db(csv_file):
    """Load the CSV data into the SQLite database with different encodings."""
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'utf-16']  # List of encodings to try

    # Try reading the CSV file with different encodings
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_file, encoding=encoding)
            break  # Exit loop if successful
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            st.write(f"Failed to load CSV with encoding: {encoding} - {e}")
    else:
        st.error("Unable to read the CSV file with the tried encodings.")
        return None  # Return None if all encodings fail

    # Replace spaces and special characters in column names with underscores
    df.columns = df.columns.str.replace('[^a-zA-Z0-9]', '_', regex=True).str.strip().str.lower()

    # If date conversion is enabled, determine date columns and convert them
    st.session_state.date_type_col = None
    if st.session_state.date_conversion:
        date_type_col = get_date_type_col(df)
        for col, fmt in date_type_col.items():
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format=fmt, errors='coerce')
        st.session_state.date_type_col = date_type_col

    # Save the DataFrame to SQLite database
    with st.session_state.engine.connect() as conn:
        df.to_sql('Data', conn.connection, if_exists='replace', index=False)

    return df


def get_date_type_col(df):
    """Determine which columns in the DataFrame are datetime and their formats."""
    client = OpenAI(api_key=openai_api_key)
    data_str = df.sample(n=10).to_string(index=False)
    completion2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": f'''
             Given the first 10 rows of data:
             {data_str}
             Identify which columns are datetime type and provide the datetime format for a strftime parser.
             Your answer should only contain a python list that is like [[column name 1, datetime format 1], [column name 2, datetime format 2]]
             If none is identified, answer []
             '''},
            {"role": "user", "content": ""}
        ]
    )

    # Extract and parse datetime column formats from the API response
    column_formats = ast.literal_eval(
        completion2.choices[0].message.content.replace("python", "").replace("```", "").strip())
    format_dict = {col: fmt for col, fmt in column_formats}
    return format_dict


def chatbot(prompt):
    """Generate SQL query to answer user prompt and fetch data from the database."""
    client = OpenAI(api_key=openai_api_key)

    query_sample = "SELECT * FROM DATA ORDER BY RANDOM() LIMIT 5;"
    try:
        with st.session_state.engine.connect() as conn:
            sample_data = pd.read_sql_query(query_sample, conn.connection)
    except SQLAlchemyError as e:
        st.error(f"Error fetching data from database: {str(e)}")
        return None, None

    sample_data_str = sample_data.to_string(index=False)

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": f'''
                 You are an expert SQLite query writer.
                 You are to respond with a SQL query needed to answer the user's question about a table.
                 The table was create from {st.session_state.file_name} and 5 sample rows from the table named DATA are:
                 {sample_data_str}
                 ------------------------------------
                 1. Use column aliases only in the SELECT clause for user-friendly display. Use alias like 'Merchant Name' instead of merchant_name.
                 2. For clauses like WHERE, GROUP BY, HAVING, and ORDER BY, you must use the original column names or expressions instead of aliases.
                 '''},
                {"role": "user", "content": prompt}
            ]
        )
    except Exception as e:
        st.error(f"Error interacting with the OpenAI API: {str(e)}")
        return None, None

    query = completion.choices[0].message.content.replace("sql", "").replace("```", "").strip()
    try:
        with st.session_state.engine.connect() as conn:
            data = pd.read_sql_query(query, conn.connection)
        return completion.choices[0].message.content, data
    except (SQLAlchemyError, Exception):
        return None, None



def main():
    st.title("SQL Chatbot on CSV Data")
    uploaded_file = st.file_uploader("Upload a CSV file to begin", type="csv", help="Only CSV files are allowed.")

    # Create two columns for file upload and options
    col1, col2 = st.columns([2, 9])
    with col1:
        if uploaded_file is not None:

            with col2:
                # Option to enable or disable datetime conversion
                st.session_state.date_conversion = st.checkbox('Convert datetime column with AI')

            if st.button("Upload"):
                st.session_state.have_data = 0
                st.session_state.messages = []
                try:
                    # Load the CSV data into the SQLite database
                    df = load_csv_to_db(uploaded_file)
                    st.session_state.file_name = uploaded_file.name
                    st.session_state.have_data = 1
                except ValueError as e:
                    st.error(f"Error occurred while loading the CSV: {e}")

    if st.session_state.have_data == 1:
        st.write(f"{st.session_state.file_name} loaded into SQLite database. Displaying first 3 rows of data from database:")
        try:
            with st.session_state.engine.connect() as conn:
                df_first_3 = pd.read_sql_query("SELECT * FROM DATA LIMIT 3", conn.connection)
            st.dataframe(df_first_3)  # Display the top 3 rows
            st.write(
                f"Columns converted to datetime type: {st.session_state.date_type_col if st.session_state.date_type_col else None}")

        except Exception as e:
            st.error(f"Error occurred while querying the database: {e}")

        st.markdown("---")

        # Welcome message for the chatbot
        welcome_message = """
            <p>Hello and welcome! 😊</p>
            <p>I’m your personal assistant, here to help you with all your dataset needs.</p>
            <p>Just ask, and I’ll help with insights, data transformations, and queries!</p>
        """

        # Initialize session state messages with the welcome message
        if not st.session_state.messages:
            st.session_state.messages.append({"role": "assistant", "content": welcome_message, "data": None})

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == 'assistant' and message["data"] is not None:
                    st.markdown(message["content"], unsafe_allow_html=True)
                    st.dataframe(message["data"])
                else:
                    st.markdown(message["content"], unsafe_allow_html=True)

        # Process user input and generate responses
        if prompt := st.chat_input("How can I help you?"):
            st.session_state.messages.append({"role": "user", "content": prompt, "data": None})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder2 = st.empty()
                message_placeholder.markdown("▌")  # Initial placeholder
                sqlquery, data = chatbot(prompt)  # Generate SQL query and fetch data
                if data is not None:
                    message_placeholder.markdown(sqlquery, unsafe_allow_html=True)
                    message_placeholder2.dataframe(data)
                    st.session_state.messages.append({"role": "assistant", "content": sqlquery, "data": data})
                else:
                    message_placeholder.markdown('Unable to create SQL query according to the input.',
                                                 unsafe_allow_html=True)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": 'Unable to create SQL query based on the input.',
                         "data": None})


if __name__ == "__main__":
    main()