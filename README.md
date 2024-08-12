# SQL Chatbot on CSV Data

## Overview

The SQL Chatbot is a Streamlit application designed to interact with CSV data through a chat interface. Users can upload CSV files, which are then processed and loaded into an SQLite database. The app leverages OpenAI's GPT to infer datetime columns, generate SQL queries, and provide insights based on user prompts.

## Features

- **CSV Upload**: Upload and process CSV files with support for multiple encodings.
- **Datetime Conversion**: Automatically convert datetime columns using AI inference.
- **SQL Query Generation**: Generate SQL queries based on user input and display results.
- **Interactive Chat Interface**: Chat-based interaction for querying and visualizing data.

## Deployment

The application is deployed on Streamlit Community Cloud. You can access it [here](https://sqldbchatbot.streamlit.app/).

## Installation

To run this application locally, follow these steps:

1. **Clone the Repository**

  ```bash
  git clone https://github.com/kentlhy/DB_Chatbot.git
  cd DB_Chatbot
  ```

2. **Create a Virtual Environment**

  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows use `venv\Scripts\activate`
  ```

3. **Install Dependencies**

  ```bash
  pip install -r requirements.txt
  ```

4. **Set Up OpenAI API Key**

Add your OpenAI API key to the Streamlit secrets. Create a file named ```secrets.toml``` in the ```.streamlit``` directory with the following content:

  ```toml
  [openai]
  api_key = "your-openai-api-key"
  ```

5. **Run the Application**

  ```bash
  streamlit run app.py
  ```

## Usage

1. **Upload a CSV File**: Use the file uploader to select and upload your CSV file.
2. **Configure Settings**: Optionally enable datetime conversion using AI.
3. **Interact with the Chatbot**: Ask questions or request data insights through the chat interface.
**Note**: The SQLite database used in this app is created dynamically during each session and does not persist between sessions. Once the session ends, the database is deleted.
