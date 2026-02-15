# csv-to-gsheets-uploader

A small Python tool that uploads a CSV file to Google Sheets.

## Features
- Upload CSV to a Google Sheet worksheet
- Overwrite mode (can be extended later)
- Basic column cleanup (trim + lowercase)
- Optional deduplication by a key column
- Optional date column parsing/formatting

## Requirements
- Python 3.10+
- A Google Cloud Service Account with Google Sheets API enabled
- A Google Sheet shared with the service account email (Editor)

## Setup (once)
1) Create a Google Cloud project and enable Google Sheets API.
2) Create a Service Account and download the JSON key file.
3) Put the key file here:
   - `config/credentials.json`
4) Create `.env` in the project root:
   - `GOOGLE_CREDS_PATH=config/credentials.json`
5) Share your Google Sheet with the service account email as Editor.

## Run
1) Install dependencies:
   - `pip install -r requirements.txt`

2) Run with sample CSV:
   - `python src/main.py --input examples/sample.csv --config config/config.example.json`

## Notes
- `.env` and `config/credentials.json` are not committed to GitHub (security).
- If you get "GOOGLE_CREDS_PATH missing", check the `.env` file and the path.
