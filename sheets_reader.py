import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account


letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def sheet_index(row, col):
    column_index = ''
    if col >= 27 * 26:
        column_index += letters[col // (27 * 26) - 1]
    if col >= 26:
        column_index += letters[(col // 26 - 1)% 26]
    column_index += letters[col % 26]
    return f'{column_index}{row + 1}'

class GoogleSheetsReader:
    def __init__(self, service_cred_file='.sheets_credentials.json', sheet_list_filename='sheet_directory.json'):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        credentials = service_account.Credentials.from_service_account_file(service_cred_file, scopes=self.scopes)
        self.service = build('sheets', 'v4', credentials=credentials)
        with open(sheet_list_filename, 'r') as file:
            self.sheet_list = json.load(file)

    def read_column(self, source_name, column_name):
        # pylint: disable=no-member
        headers = self.__read_row(**self.sheet_list[source_name], row_number=1)
        column_indexes = {name:index for index, name in enumerate(headers)}
        if column_name not in column_indexes:
            return []
        
        sheet = self.service.spreadsheets() #py-lint ignore
        id = self.sheet_list[source_name]['sheet_id']
        name = self.sheet_list[source_name]['sheet_name']
        column = column_indexes[column_name]
        start_range = sheet_index(1, column)
        end_range = sheet_index(1000, column)
        result = sheet.values().get(spreadsheetId=id, majorDimension='COLUMNS', range=f'{name}!{start_range}:{end_range}').execute()

        return result.get('values', [])[0]


    def read_row_from_source(self, source_name, row_number, as_dict=False):
        # print(self.sheet_list[source_name])
        if as_dict:
            headers = self.__read_row(**self.sheet_list[source_name], row_number=1)
            data = self.__read_row(**self.sheet_list[source_name], row_number=row_number)
            return {k:v for k, v in zip(headers, data)}
        return self.__read_row(**self.sheet_list[source_name], row_number=row_number)

    def __read_row(self, sheet_id, sheet_name, row_number):
        # pylint: disable=no-member
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range=f'{sheet_name}!A{row_number}:ZZZ{row_number}').execute()
        values = result.get('values', [])
        return values[0]


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    sheets_reader = GoogleSheetsReader('service_credentials.json')

    # print("Reading in a row")
    # print(sheets_reader.read_row_from_source('recipes', 5))

    # print("Reading in a row with the headers")
    # print(sheets_reader.read_row_from_source('recipes', 7, as_dict=True))

    print("Reading in a column")
    print(sheets_reader.read_column('recipes', 'Recipe Name'))
    
if __name__ == '__main__':
    main()