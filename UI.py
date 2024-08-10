import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from openai import OpenAI
import os


# Define the path to the SQLite database
DB_PATH = 'fraud.db'

engine = create_engine(f'sqlite:///{DB_PATH}', echo=True)

if 'have_data' not in st.session_state:
    st.session_state.have_data = 0
openai_api_key = st.secrets["openai"]["api_key"]
os.environ["OPENAI_API_KEY"] = openai_api_key

def load_csv_to_db(csv_file):
    """Load the CSV data into the SQLite database."""
    df = pd.read_csv(csv_file, infer_datetime_format=True)

    """Clean column names by removing spaces and special characters."""
    df.columns = df.columns.str.replace('[^a-zA-Z0-9]', '_', regex=True).str.strip().str.lower()
    # Display the data types
    print(df.dtypes)

    with engine.connect() as conn:
        df.to_sql('Data', conn.connection, if_exists='replace', index=False)

    return df

def chatbot(prompt, engine):
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=openai_api_key, )

    query = "SELECT * FROM Data LIMIT 5"
    with engine.connect() as conn:
        data = pd.read_sql_query(query, conn.connection)
    data_str = data.to_string(index=False)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": f'''You are an expert sqlite sql query writer.
             You are to respond with a sql query needed to answer the user's question about a table.
             The first 5 rows of data from the table named Data are: {data_str}
             ------------------------
             If you recognise datetime data, include a parser based of the value to format a proper query.
             Always use user friendly alias for each retrieved column for clarity.'''},
            {"role": "user", "content": prompt}
        ]
    )
    query2 = completion.choices[0].message.content.replace("sql", "").replace("```", "").strip()
    try:
        with engine.connect() as conn:
            data2 = pd.read_sql_query(query2, conn.connection)
        return completion.choices[0].message.content, data2
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return completion.choices[0].message.content, None


def main():
    st.title("Chatbot on CSV data")

    uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

    if uploaded_file is not None and st.button("Upload"):
        st.write("Loading CSV data into the database...")

        # Load CSV data into the SQLite database
        df = load_csv_to_db(uploaded_file)

        st.session_state.have_data = 1

    if st.session_state.have_data == 1:
        # Get the top 3 rows
        query = "SELECT * FROM Data LIMIT 3"
        with engine.connect() as conn:
            df_first_3 = pd.read_sql_query(query, conn.connection)

        # Display the top 3 rows
        st.write("Top 3 rows of the data:")
        st.dataframe(df_first_3)

        # Display the data types
        st.write("Data types of the columns:")
        st.write(df_first_3.dtypes)


        # Chat interface
        welcome_message = """
            <p>Hello there! 😊</p>
            <p>Welcome to your personal assistant! I’m here to help you answer everything about the dataset. 🎉</p>
            <p>Feel free to ask any questions you have! 🎊</p>
        """

        # Initialize session state variables
        if "messages" not in st.session_state:
            st.session_state.messages = []
            # Add welcome message to the session state messages
            st.session_state.messages.append({"role": "assistant", "content": welcome_message})

        # Loop for showing chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)  # Allow HTML for formatting

        # Code runs when a new user input comes
        if prompt := st.chat_input("How can I help you?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("▌")  # Initial placeholder
                # Call the chatbot function with the user input as the description
                sqlquery, data = chatbot(prompt, engine)  # Call the chatbot function
                if data is not None:
                    data_html = data.to_html(classes='table table-striped')
                    message_placeholder.markdown(sqlquery + '\n' + data_html, unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": sqlquery + '\n' + data_html})
                else:
                    message_placeholder.markdown('Unable to create SQL query according to the input.', unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": 'Unable to create SQL query according to the input.'})

if __name__ == "__main__":
    main()