import json
import gspread
import argparse


from config import DEFAULT_FILE_PATH, PASSWORD, EMAIL, COL_COUNT, WORK_SHEET, DOCUMENT_ID


def load_data(file_name):
    return json.loads(open(file_name).read())

def insert_data(data):
    gc = gspread.login(EMAIL, PASSWORD)
    sh = gc.open_by_key(DOCUMENT_ID)
    worksheet = sh.add_worksheet(title=WORK_SHEET, rows=len(data.keys()), cols=COL_COUNT)

    for i, (k, v) in enumerate(data.items(), 1):
        worksheet.update_cell(i, 1, k)
        worksheet.update_cell(i, 2, v)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', help='data file path', default=DEFAULT_FILE_PATH)
    results = parser.parse_args()
    data = load_data(results.name)
    insert_data(data)
