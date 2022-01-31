from xlrd import open_workbook
import csv
import argparse
import logging

def extract_csv_form_excel(excel_file, path_to_save_csv):

    wb = open_workbook(excel_file)

    for i in range(2, wb.nsheets):

        sheet = wb.sheet_by_index(i)
        csv_name = sheet.name.replace(" ", "").lower()

        logging.info("Opening and Generating CSV for Sheet: '{}'".format(sheet.name))

        with open("{}/{}-old.csv".format(path_to_save_csv, csv_name), "w") as file:
            writer = csv.writer(file, delimiter=",")

            logging.info("Sheet '{}' has '{}' columns and '{}' rows".format(sheet.name, sheet.ncols, sheet.nrows))
            header = [cell.value for cell in sheet.row(0)]

            writer.writerow(header)

            for row_idx in range(1, sheet.nrows):
                row = [int(cell.value) if isinstance(cell.value, float) else cell.value
                       for cell in sheet.row(row_idx)]
                writer.writerow(row)
            logging.info("Generated CSV '{}.csv' at {}".format(csv_name, path_to_save_csv))

def setup_argparser():

    parser = argparse.ArgumentParser(description="Pass in the Last Quarter's Audit *.xlsx file and the script will generate csvs for all ")

    parser.add_argument('--excel_sheet',
                        help="1. Pass in last quarter's audit sheet",
                        required=True)

    parser.add_argument('--path_to_save_csv',
                        help="Mention Path to Store CSV",
                        required=True)

    parser.add_argument('--logging_level',
                        choices=['debug', 'info'],
                        help="DEFAULT is INFO",
                        default="info",
                        required=False)

    return parser.parse_args()


def setup_logging(logging_level):

    if logging_level == 'debug':
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')


def main():

    # Setup argparser
    args = setup_argparser()

    # Setup logging
    setup_logging(args.logging_level)

    # Extract CSV from Excel Sheet
    extract_csv_form_excel(args.excel_sheet, args.path_to_save_csv)



if __name__ == '__main__':
    main()