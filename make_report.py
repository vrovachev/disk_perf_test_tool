import sys
import json
import gspread
import argparse


from config import DEFAULT_FILE_PATH, PASSWORD, EMAIL, COL_COUNT, WORK_SHEET, DOCUMENT_ID


def load_data(file_name):
    if file_name == '-':
        data = sys.stdin.read()
    else:
        data = open(file_name).read()
    return json.loads(data)

def insert_data(data):
    gc = gspread.login(EMAIL, PASSWORD)
    sh = gc.open_by_key(DOCUMENT_ID)
    worksheet = sh.add_worksheet(title=WORK_SHEET, rows=len(data.keys()), cols=COL_COUNT)

    for i, (k, v) in enumerate(data.items(), 1):
        worksheet.update_cell(i, 1, k)
        worksheet.update_cell(i, 2, v)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file_name',
                        help='data file path', 
                        default='-')
    results = parser.parse_args(argv)
    data = load_data(results.name)
    insert_data(data)


if __name__ == '__main__':
    exit(main(sys.argv[1:]))
