import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)



def clean_dataframe(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    report = {
        "rows_in": int(len(df)),
        "rows_out": None,
        "duplicates_removed": 0,
        "invalid_dates": 0,
        "columns": list(df.columns),
    }

    if cfg.get("lowercase_columns", True):
        df.columns = [str(c).strip().lower() for c in df.columns]
    else:
        df.columns = [str(c).strip() for c in df.columns]

    if cfg.get("trim_whitespace", True):
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.strip()

    date_cols = cfg.get("date_columns", []) or []
    for col in date_cols:
        col_norm = col.strip().lower() if cfg.get("lowercase_columns", True) else col.strip()
        if col_norm in df.columns:
            before = df[col_norm].isna().sum()
            df[col_norm] = pd.to_datetime(df[col_norm], errors="coerce")
            after = df[col_norm].isna().sum()
            report["invalid_dates"] += int(after - before)
            df[col_norm] = df[col_norm].dt.strftime("%Y-%m-%d %H:%M:%S")

    dedupe_key = cfg.get("dedupe_key")
    if dedupe_key:
        key_norm = dedupe_key.strip().lower() if cfg.get("lowercase_columns", True) else dedupe_key.strip()
        if key_norm in df.columns:
            before = len(df)
            df = df.drop_duplicates(subset=[key_norm], keep="first")
            report["duplicates_removed"] = int(before - len(df))

    report["rows_out"] = int(len(df))
    return df, report


def gsheets_client(creds_path: str):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)


def write_to_sheet(gc, sheet_name: str, worksheet_name: str, df: pd.DataFrame, mode: str):
    try:
        sh = gc.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(sheet_name)

    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=26)

    values = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()

    if mode == "append":
        existing = ws.get_all_values()
        if not existing:
            ws.update(values)
        else:
            ws.append_rows(values[1:], value_input_option="RAW")
    else:
        ws.clear()
        ws.update(values)

    return sh.url


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="CSV Cleaner + Google Sheets Uploader")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--mode", choices=["overwrite", "append"], default=None, help="Override mode")
    args = parser.parse_args()

    cfg = load_config(args.config)

    creds_path = os.getenv("GOOGLE_CREDS_PATH")
    if not creds_path or not os.path.exists(creds_path):
        log("ERROR: GOOGLE_CREDS_PATH missing or file not found. Put creds JSON and set .env")
        sys.exit(1)

    log("Reading CSV...")
    df = pd.read_csv(args.input)

    log("Cleaning data...")
    df_clean, report = clean_dataframe(df, cfg)

    log(f"Rows in: {report['rows_in']} | Rows out: {report['rows_out']} | Duplicates removed: {report['duplicates_removed']} | Invalid dates: {report['invalid_dates']}")

    log("Connecting to Google Sheets...")
    gc = gsheets_client(creds_path)

    sheet_name = cfg.get("sheet_name", "CSV Import")
    worksheet_name = cfg.get("worksheet_name", "data")
    mode = cfg.get("mode", "overwrite")

    log(f"Uploading to Sheet='{sheet_name}' Worksheet='{worksheet_name}' Mode='{mode}' ...")
    url = write_to_sheet(gc, sheet_name, worksheet_name, df_clean, mode)

    log(f"DONE. Sheet URL: {url}")


if __name__ == "__main__":
    main()
