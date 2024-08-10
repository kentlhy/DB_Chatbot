import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os

# Define the path to the SQLite database
DB_PATH = 'fraud.db'

def load_csv_to_db(csv_file, engine):
    """Load the CSV data into the SQLite database."""
    df = pd.read_csv(csv_file)
    with engine.connect() as conn:
        df.to_sql('fraud', conn.connection, if_exists='replace', index=False)

def main():
    st.title("CSV to SQLite App with SQLAlchemy")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        st.write("Loading CSV data into the database...")

        # Create a SQLAlchemy engine
        engine = create_engine('sqlite:///fraud.db', echo=True)

        # Load CSV data into the SQLite database
        load_csv_to_db(uploaded_file, engine)

        # Get the top 3 rows
        query = "SELECT * FROM fraud LIMIT 3"
        with engine.connect() as conn:
            df_first_3 = pd.read_sql_query(query, conn.connection)

        # Display the top 3 rows
        st.write("Top 3 rows of the data:")
        st.dataframe(df_first_3)

if __name__ == "__main__":
    main()