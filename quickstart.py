import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_credentials():
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

    return credentials

if __name__ == "__main__":
    gc = gspread.authorize(get_credentials())

    wks = gc.open_by_key("1ANGfPyMJK-fjLYlX7VoOGf0CUy38_tY5YiCWIxN6Kx8").sheet1
