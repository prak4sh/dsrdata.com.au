from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from rich import print

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

class SheetManager:
    def __init__(self, title, creds_path='credentials.json', token_path='token.json'):
        self.title = title
        self.creds_path = creds_path
        self.token_path = token_path
        self.creds = self.get_creds(token_path)
        self.service = self.connect_to_sheets(self.creds)
        self.sheet_id = self.ensure_sheet(title)

    def time_now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def print_info(self, msg, mtype='INF'):
        if mtype == 'INF':
            print(f"[green]{self.time_now()} [INF][/green] {msg}")
        elif mtype == 'ERR':
            self.log_error(msg)
            print(f"[red]{self.time_now()} [ERR][/red] {msg}")
        elif mtype == 'WRN':
            print(f"[yellow]{self.time_now()} [WRN][/yellow] {msg}")
        else:
            print(f"[{mtype}] {msg}")

    def log_error(self, msg):
        with open("error.log", "a") as f:
            f.write(f"{self.time_now()} [ERR] {msg}\n")

    def get_creds(self, token_file="token.json"):
        self.print_info('Getting token for Google APIs...')
        if os.path.exists(token_file):
            return Credentials.from_authorized_user_file(token_file, SCOPES)
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        return creds

    def ensure_sheet(self, title):
        load_dotenv()
        sheet_id = os.environ.get("SHEET_ID")
        try:
            if sheet_id:
                self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                # print_info(f"Sheet exists: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
                return sheet_id
        except Exception as e:
            self.print_info(f"Sheet not found or inaccessible: {e}", mtype='WRN')
        try:
            spreadsheet = {
                'properties': {'title': title}
            }
            sheet = self.service.spreadsheets().create(body=spreadsheet).execute()
            new_sheet_id = sheet['spreadsheetId']
            self.print_info(f"Created new sheet: https://docs.google.com/spreadsheets/d/{new_sheet_id}/edit")
            # Save new SHEET_ID to .env
            env_path = ".env"
            if os.path.exists(env_path):
                with open(env_path, "r") as env_file:
                    lines = env_file.readlines()
                with open(env_path, "w") as env_file:
                    for line in lines:
                        if not line.startswith("SHEET_ID="):
                            env_file.write(line)
                    env_file.write(f"SHEET_ID={new_sheet_id}\n")
            else:
                with open(env_path, "w") as env_file:
                    env_file.write(f"SHEET_ID={new_sheet_id}\n")
            return new_sheet_id
        except Exception as e:
            self.print_info(f"Error creating sheet: {e}", mtype='ERR')
            return None

    def connect_to_sheets(self, creds):
        if not creds:
            self.print_info("Invalid or missing credentials for Google Sheets API", mtype='ERR')
            return None
        try:
            service = build('sheets', 'v4', credentials=creds)
            self.print_info("Connected to Google Sheets API")
            return service
        except Exception as e:
            self.print_info(f"Error connecting to Google Sheets API: {e}", mtype='ERR')
            return None
        
    def log_to_sheet(self, info):
        if not self.service:
            self.print_info("No valid Google Sheets connection", mtype='ERR')
            return
        if not self.sheet_id:
            self.print_info("No valid sheet ID", mtype='ERR')
            return
        try:
            range_name = "Sheet1!A1:Z1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            headers = result.get('values', [])
            info_keys = list(info.keys())

            # If no headers, write them
            if not headers or headers[0] != info_keys:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.sheet_id,
                    range="Sheet1!A1",
                    valueInputOption="RAW",
                    body={'values': [info_keys]}
                ).execute()

            # Append the row
            values = [list(info.values())]
            body = {'values': values}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range="Sheet1!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            self.print_info(f"Logged info to Google Sheet: {result.get('updates').get('updatedCells')} cells appended")
        except Exception as e:
            self.print_info(f"Error logging to Google Sheet: {e}", mtype='ERR')

if __name__ == "__main__":
    manager = SheetManager("DSR Data")
    sample_info = {
        "Timestamp": manager.time_now(),
        "Data Point 1": "Value 1",
        "Data Point 2": "Value 2"
    }
    manager.log_to_sheet(sample_info)


