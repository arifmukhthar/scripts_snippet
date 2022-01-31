import csv
import os
import argparse
import logging
from os import listdir
from os.path import isfile, join


class EmailNormalizer:

    def check_if_file_exists(self, sheet):
        cwd = os.getcwd()
        file_exists = os.path.isfile('{}/{}'.format(cwd, sheet))
        return file_exists

    def generate_useremail_csv(self, all_useremail_set_normalized, service_type):
        sheet = "{}/all_useremail_sheet_{}.csv".format(os.getcwd(), service_type)
        file_exists = self.check_if_file_exists(sheet)

        with open(sheet, mode='w') as all_useremail_sheet:
            all_useremail_file = csv.DictWriter(all_useremail_sheet, fieldnames=["email"])

            if not file_exists:
                all_useremail_file.writeheader()
            for user_email in all_useremail_set_normalized:
                all_useremail_file.writerow({'email': user_email})

    def prepare_normalized_email_set(self, all_useremail_set):

        # Parses Emails to lower case and only returns emails in Pearson Domain
        all_username_set_normalized = set()

        for useremail in all_useremail_set:
            try:
                useremail = useremail.lower()
                useremail_domain = useremail.lower().split("@")[1]
            except Exception:
                logging.debug("Bad User Email Data found while normalizing")
                continue

            if 'pearson' in useremail_domain:
                all_username_set_normalized.add(useremail)
            else:
                logging.debug("Useremail '{}' not in Pearson Domain - Discarding as it won't exist in Fusion Directory anyways".format(useremail))

        return all_username_set_normalized


class UserIndexer:

    def get_all_users_from_jenkins_csv(self, csv_files_list):
        all_useremail_set = set()

        for file in csv_files_list:
            with open(file, mode='r') as csv_file:
                reader = csv.DictReader(csv_file, fieldnames=(
                    "Username", "Full_Name", "Email"))

                next(reader)
                for row in reader:
                    email = row['Email']
                    if email is not None and not "":
                        all_useremail_set.add(email)
        return all_useremail_set

    def get_all_users_from_erps_csv(self, csv_files_list):
        all_useremail_set = set()

        for file in csv_files_list:
            with open(file, mode='r') as csv_file:
                reader = csv.DictReader(csv_file, fieldnames=(['key']))

                next(reader)
                for row in reader:
                    email = row['key']
                    if email is not None and not "":
                        all_useremail_set.add(email)
        return all_useremail_set

    def get_all_users_from_bitbucket_csv(self, csv_files_list):
        all_useremail_set = set()

        for file in csv_files_list:
            with open(file, mode='r') as csv_file:
                reader = csv.DictReader(csv_file, fieldnames=("DISPLAY NAME","USERNAME","EMAIL ADDRESS","IS ACTIVE","PERMISSION"))

                next(reader)
                for row in reader:
                    email = row['EMAIL ADDRESS']
                    if email is not None and not "":
                        all_useremail_set.add(email)
        return all_useremail_set

    def get_all_users_from_sonar_csv(self, csv_files_list):
        all_useremail_set = set()

        for file in csv_files_list:
            with open(file, mode='r') as csv_file:
                reader = csv.DictReader(csv_file, fieldnames=("USERNAME","FULL NAME","EMAIL","IS ACTIVE","GROUPS"))

                next(reader)
                for row in reader:
                    email = row['EMAIL']
                    if email is not None and not "":
                        all_useremail_set.add(email)
        return all_useremail_set

    def get_all_users_from_aws_csv(self, csv_files_list):
        all_useremail_set = set()

        for file in csv_files_list:
            with open(file, mode='r') as csv_file:
                reader = csv.DictReader(csv_file, fieldnames=(['email']))

                next(reader)
                for row in reader:
                    email = row['email']
                    if email is not None and not "":
                        all_useremail_set.add(email)
        return all_useremail_set

    def get_all_users_from_all_csv(self, csv_files_list):
        all_useremail_set = set()

        for file in csv_files_list:
            with open(file, mode='r') as csv_file:
                reader = csv.DictReader(csv_file, fieldnames=(['email']))

                next(reader)
                for row in reader:
                    email = row['email']
                    if email is not None and not "":
                        all_useremail_set.add(email)
        return all_useremail_set



    def get_all_user_email_from_csv(self, csv_directory, service_type):
        csv_files_list = [join(csv_directory, f) for f in listdir(csv_directory) if isfile(join(csv_directory, f))]
        all_useremail_set = set()

        if service_type == 'jenkins':
            all_useremail_set = self.get_all_users_from_jenkins_csv(csv_files_list)
        elif service_type == 'erps':
            all_useremail_set = self.get_all_users_from_erps_csv(csv_files_list)
        elif service_type == 'bitbucket':
            all_useremail_set = self.get_all_users_from_bitbucket_csv(csv_files_list)
        elif service_type == 'sonar':
            all_useremail_set = self.get_all_users_from_sonar_csv(csv_files_list)
        elif service_type == 'aws':
            all_useremail_set = self.get_all_users_from_aws_csv(csv_files_list)
        elif service_type == 'all':
            all_useremail_set = self.get_all_users_from_all_csv(csv_files_list)

        return all_useremail_set


def setup_argparser():

    parser = argparse.ArgumentParser(description="Pass in a Directory Path with CSV files form user-audit.sh and the scripts parses all files and outputs a CSV with Unique Pearson Email IDs of all users")

    parser.add_argument('--csv_directory',
                        help="1. Pass in a Directory Absolute Path with CSVs containing all User's Pearson Email.",
                        required=True)

    parser.add_argument('--service_type',
                        choices=['jenkins', 'zabbix', 'erps', 'bitbucket', 'sonar', 'aws', 'all'],
                        help='Specify the service for which new csv with all Pearson Email ID has to be generated. Use ALL option only at the end after generating CSVs for all other services to generate a final CSV file with Pearson Email IDs from all other services CSVs.',
                        required=True)

    parser.add_argument('--logging_level',
                        choices=['debug', 'info'],
                        help="Specify the logging level and monitor get-all-user-emails.log file. \n DEFAULT is INFO. ",
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

    # Setup Indexer to get User's Pearson Email from all CSV files and prepare a Set of unique User Email Addresses
    indexer = UserIndexer()
    all_useremail_set = indexer.get_all_user_email_from_csv(csv_directory=args.csv_directory, service_type=args.service_type)

    # Normalize all_usermail_set and write them to new CSV
    normalizer = EmailNormalizer()
    all_useremail_set_normalized = normalizer.prepare_normalized_email_set(all_useremail_set)
    normalizer.generate_useremail_csv(all_useremail_set_normalized, args.service_type)


if __name__ == "__main__":
    main()