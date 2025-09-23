from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from rich import print
import pandas as pd
import numpy as np

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
        
    def get_or_create_sheet(self, sheet_name):
        """
        Get sheet ID by name, or create it if it doesn't exist.
        Returns the sheet ID (gid) of the specified sheet.
        """
        try:
            # Get spreadsheet metadata to check existing sheets
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            
            # Check if sheet with given name already exists
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    self.print_info(f"Found existing sheet: {sheet_name}")
                    return sheet_id
            
            # Sheet doesn't exist, create it
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={'requests': requests}
            ).execute()
            
            new_sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            self.print_info(f"Created new sheet: {sheet_name}")
            return new_sheet_id
            
        except Exception as e:
            self.print_info(f"Error getting/creating sheet '{sheet_name}': {e}", mtype='ERR')
            return None

    def log_to_sheet(self, info, sheet_name="Sheet1"):
        """
        Log data to sheet - handles both single dict and list of dicts
        """
        if isinstance(info, list):
            self.log_batch_to_sheet(info, sheet_name)
        elif isinstance(info, dict):
            self.log_batch_to_sheet([info], sheet_name)
        else:
            self.print_info("Invalid data format. Expected dict or list of dicts", mtype='ERR')

    def log_batch_to_sheet(self, data_list, sheet_name="Sheet1"):
        """
        Log a list of dictionaries to sheet in a single batch operation.
        """
        if not self.service:
            self.print_info("No valid Google Sheets connection", mtype='ERR')
            return
        if not self.sheet_id:
            self.print_info("No valid sheet ID", mtype='ERR')
            return
        if not data_list:
            self.print_info("No data to log", mtype='WRN')
            return
        
        try:
            # Ensure the sheet exists
            sheet_gid = self.get_or_create_sheet(sheet_name)
            if sheet_gid is None:
                self.print_info(f"Failed to get or create sheet: {sheet_name}", mtype='ERR')
                return
            
            # Get headers from first dictionary
            headers = list(data_list[0].keys())
            
            # Prepare all data rows
            all_values = [headers]  # Start with headers
            
            # Add all data rows - handle NaN values
            for data in data_list:
                row = []
                for header in headers:
                    value = data.get(header, '')
                    # Convert NaN, None, and other problematic values to empty string
                    if pd.isna(value) or value is None or str(value).lower() == 'nan':
                        row.append('')
                    else:
                        # Convert to string to ensure JSON serialization
                        row.append(str(value))
                all_values.append(row)

            # Clear and write everything
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!A:Z"
            ).execute()
            
            # Write all data
            body = {'values': all_values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body=body
            ).execute()
            
            cells_updated = result.get('updatedCells', 0)
            self.print_info(f"Batch logged {len(data_list)} records to sheet '{sheet_name}': {cells_updated} cells updated")
            
        except Exception as e:
            self.print_info(f"Error batch logging to Google Sheet '{sheet_name}': {e}", mtype='ERR')

def main():
    manager = SheetManager("DSR Data")
    sample_info = {
        "Timestamp": manager.time_now(),
        "Data Point 1": "Value 1",
        "Data Point 2": "Value 2"
    }
    manager.log_to_sheet(sample_info)

    # Batch logging example
    batch_data = [
        {
            "Timestamp": manager.time_now(),
            "Data Point 1": "Batch Value 1",
            "Data Point 2": "Batch Value 2"
        },
        {
            "Timestamp": manager.time_now(),
            "Data Point 1": "Batch Value 3",
            "Data Point 2": "Batch Value 4"
        }
    ]
    manager.log_batch_to_sheet(batch_data)

if __name__ == "__main__":
    main()


