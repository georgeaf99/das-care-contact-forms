import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_NAME_TO_ID = dict(
    COPY_VISITOR_FORM_RESPONSES="1ANGfPyMJK-fjLYlX7VoOGf0CUy38_tY5YiCWIxN6Kx8"
)

def get_credentials():
    """Gets credentials needed to access the spreadsheet"""
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

    return credentials

def format_responses(responses_wks):
    """Format the data in the worksheet into list of dicts

    @param responses_wks The worksheet to load data from
    @return List of row mappings from column name to cell value
    """
    # The column names are in the first row
    schema = responses_wks.row_values(1)
    row_values = responses_wks.get_all_values()[1:]

    return [
        dict((
            (col_name, cell_val)
            for col_name, cell_val in zip(schema, response)
            if cell_val != ''
        ))
        for response in row_values
    ]

if __name__ == "__main__":
    gc = gspread.authorize(get_credentials())

    spreadsheet = gc.open_by_key(SPREADSHEET_NAME_TO_ID["COPY_VISITOR_FORM_RESPONSES"])
    responses_wks = spreadsheet.get_worksheet(0)

    resps = format_responses(responses_wks)
