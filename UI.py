import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import os

def load_csv_to_db(csv_file, engine):
    """Load the CSV data into the SQLite database, replacing the existing table."""
    df = pd.read_csv(csv_file)
    try:
        df.to_sql('data', engine, if_exists='replace', index=False)
        st.success("CSV data loaded successfully and table replaced.")
    except SQLAlchemyError as e:
        st.error(f"An error occurred while loading data into the database: {e}")

def get_top_3_rows(engine):
    """Query the database to return the top 3 rows."""
    query = "SELECT * FROM data LIMIT 3"
    try:
        return pd.read_sql_query(query, engine)
    except SQLAlchemyError as e:
        st.error(f"An error occurred while querying the database: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of an error

def main():
    st.title("CSV to Permanent SQLite with SQLAlchemy")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        st.write("Loading CSV data into the database...")

        # Create an SQLAlchemy engine for the permanent SQLite database
        engine = create_engine(f'sqlite:///fraud.db')

        # Load CSV data into the SQLite database
        load_csv_to_db(uploaded_file, engine)

        # Get the top 3 rows
        top_3_rows = get_top_3_rows(engine)

        # Display the top 3 rows
        if not top_3_rows.empty:
            st.write("Top 3 rows of the data:")
            st.dataframe(top_3_rows)

if __name__ == "__main__":
    main()