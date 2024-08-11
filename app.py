import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table
from openai import OpenAI
import time
import ast

if 'have_data' not in st.session_state:
    st.session_state.have_data = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if 'date_conversion' not in st.session_state:
    st.session_state.date_conversion = False
if 'db_type' not in st.session_state:
    st.session_state.db_type = None
if 'engine' not in st.session_state:
    st.session_state.engine = None

openai_api_key = st.secrets["openai"]["api_key"]

def load_csv_to_db(csv_file):
    """Load the CSV data into the SQLite database with different encodings."""
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'utf-16']

    for enc in encodings:
        try:
            df = pd.read_csv(csv_file, encoding=enc)
            print(f"Successfully loaded CSV with encoding: {enc}")
            break  # Exit loop if reading is successful
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            print(f"Failed to load CSV with encoding: {enc} - {e}")
    else:
        # If the loop completes without a break, it means all encodings failed
        raise ValueError("Unable to read the CSV file with the tried encodings.")

    # Replace space and special characters in column name by _
    df.columns = df.columns.str.replace('[^a-zA-Z0-9]', '_', regex=True).str.strip().str.lower()
    st.session_state.date_type_col = None
    if st.session_state.date_conversion:
        print("AI conversion is on")
        date_type_col = get_date_type_col(df)
        # Convert columns to datetime
        for col, fmt in date_type_col.items():
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format=fmt, errors='coerce')
        st.session_state.date_type_col = date_type_col
        print(df.dtypes)

    with st.session_state.engine.connect() as conn:
        df.to_sql('Data', conn.connection, if_exists='replace', index=False)

    return df

def get_date_type_col(df):
    client = OpenAI(api_key=openai_api_key, )
    data_str = df.head(10).to_string(index=False)
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
    print(completion2.choices[0].message.content)
    # Parse the string into a Python list
    column_formats = ast.literal_eval(completion2.choices[0].message.content.replace("python", "").replace("```", "").strip())

    # Convert list of columns and formats into a dictionary
    format_dict = {col: fmt for col, fmt in column_formats}
    return format_dict


def chatbot(prompt):
    client = OpenAI(api_key=openai_api_key, )

    query = "SELECT * FROM Data LIMIT 5"
    with st.session_state.engine.connect() as conn:
        data = pd.read_sql_query(query, conn.connection)
    data_str = data.to_string(index=False)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": f'''
             You are an expert {st.session_state.db_type} sql query writer.
             You are to respond with a sql query needed to answer the user's question about a table.
             The first 5 rows of data from the table named Data are:
             {data_str}
             ------------------------
             If you recognise datetime data such as 04-01-2019 00:58, include a strftime parser to format the full datetime before querying.
             Always use user readable alias like 'Merchant Name' instead of merchant_name for each retrieved column for clarity.
             '''},
            {"role": "user", "content": prompt}
        ]
    )

    query2 = completion.choices[0].message.content.replace("sql", "").replace("```", "").strip()
    try:
        with st.session_state.engine.connect() as conn:
            data2 = pd.read_sql_query(query2, conn.connection)
        return completion.choices[0].message.content, data2
    except Exception as e:
        return None, None

def main():
    st.title("SQL Chatbot on CSV Data")
    uploaded_file = st.file_uploader("Upload a CSV file to begin", type="csv", help="Only CSV files are allowed.")
    # Create two columns: one for the button and one for the success message container
    col1, col2, col3 = st.columns([1, 2, 4])
    with col1:
        if uploaded_file is not None:
            with col2:
                # Create the message container in col2
                st.session_state.date_conversion = st.checkbox('AI date conversion')
            with col3:
                # Create the radio button widget
                st.session_state.db_type = st.radio("Type of DB:", ["SQLite", "MySQL", "PostgreSQL"])

            if st.button("Upload"):
                st.session_state.have_data = 0
                st.session_state.messages = []
                try:
                    # Define the path to the database
                    if st.session_state.db_type == "SQLite":
                        st.session_state.engine = create_engine('sqlite:///data.db', echo=False)
                    elif st.session_state.db_type == "MySQL":
                        st.session_state.engine = create_engine('mysql+pymysql://user:password@host/dbname', echo=False)
                    elif st.session_state.db_type == "PostgreSQL":
                        st.session_state.engine = create_engine('postgresql+psycopg2://user:password@host/dbname', echo=False)
                    else:
                        st.error("Select a database type.")

                    # Load CSV data into the SQLite database
                    df = load_csv_to_db(uploaded_file)
                    st.session_state.have_data = 1
                except ValueError as e:
                    # Update the message container
                    st.error(f"Error occurred while loading the CSV: {e}")

    if st.session_state.have_data == 1:

        st.write(f"CVS loaded to {st.session_state.db_type} database. First 3 rows of data from the database:")
        try:
            with st.session_state.engine.connect() as conn:
                df_first_3 = pd.read_sql_query("SELECT * FROM Data LIMIT 3", conn.connection)
            # Display the top 3 rows
            st.dataframe(df_first_3)
            st.write(f"Columns converted to datetime type: {st.session_state.date_type_col if st.session_state.date_type_col else None}")

        except Exception as e:
            st.error(f"Error occurred while querying the database: {e}")

        st.markdown("---")

        welcome_message = """
            <p>Hello there! 😊</p>
            <p>Welcome to your personal assistant! I’m here to help you answer everything about the dataset.</p>
        """

        # Initialize session state variables
        if not st.session_state.messages:
            # Add welcome message to the session state messages
            st.session_state.messages.append({"role": "assistant", "content": welcome_message, "data": None})

        # Loop for showing chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == 'assistant' and message["data"] is not None:
                    st.markdown(message["content"], unsafe_allow_html=True)
                    st.dataframe(message["data"])
                else:
                    st.markdown(message["content"], unsafe_allow_html=True)

        # Code runs when a new user input comes
        if prompt := st.chat_input("How can I help you?"):
            st.session_state.messages.append({"role": "user", "content": prompt, "data": None})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder2 = st.empty()
                message_placeholder.markdown("▌")  # Initial placeholder
                # Call the chatbot function with the user input as the description
                sqlquery, data = chatbot(prompt)  # Call the chatbot function
                if data is not None:
                    #data_html = data.to_html(classes='table table-striped')
                    message_placeholder.markdown(sqlquery, unsafe_allow_html=True)
                    message_placeholder2.dataframe(data)
                    st.session_state.messages.append({"role": "assistant", "content": sqlquery, "data": data})
                else:
                    message_placeholder.markdown('Unable to create SQL query according to the input.', unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": 'Unable to create SQL query based on the input.', "data": None})

if __name__ == "__main__":
    main()