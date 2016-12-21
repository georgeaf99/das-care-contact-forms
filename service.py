import json
import os

from oauth2client.service_account import ServiceAccountCredentials

import gspread


config_store = None
spreadsheet_client = None
forms_version = None
main_spreadsheet = None
main_spreadsheet_name = None

def get_credentials():
    """Gets credentials needed to access the spreadsheet"""
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

    return credentials


# Load the config
with open(os.path.abspath('./config.json'), "r") as f:
    config_store = json.loads(f.read())

spreadsheet_client = gspread.authorize(get_credentials())
forms_version = config_store['forms_version']
main_spreadsheet = spreadsheet_client.open_by_key(config_store['main_spreadsheet']['id'])
main_spreadsheet_name = config_store['main_spreadsheet']['name']
