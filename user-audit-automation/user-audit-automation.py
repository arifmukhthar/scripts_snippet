import csv
import json
import os
import argparse
import logging

global terminated_employee_list

class CsvHelper:

    __csv_helper = None

    def check_if_file_exists(self, csv_file):
        cwd = os.getcwd()
        file_exists = os.path.isfile('{}/{}'.format(cwd, csv_file))
        return file_exists

    def write_to_new_csv(self, user_data, csv_headers):

        csv_file = "{}-audited.csv".format(self.csv_name)

        file_exists = self.check_if_file_exists(csv_file)

        with open(csv_file, mode='a') as audited_sheet:
            audited_file = csv.DictWriter(audited_sheet, fieldnames=csv_headers)
            if not file_exists:
                audited_file.writeheader()
            audited_file.writerow(user_data)

    @staticmethod
    def get_csv_helper(self, csv_name):

        if self.__csv_helper is None:
            self.csv_name = csv_name
        return self.__csv_helper

class TerminatedEmployee:

    def get_all_terminated_users_csv(self, terminated_employee_csv):

        terminated_employees = []
        with open(terminated_employee_csv, mode='r') as csv_file:
            reader = csv.DictReader(csv_file, fieldnames=(['email']))

            next(reader)
            for row in reader:
                email = row['email']
                if email is not None and not "":
                    terminated_employees.append(email)
        return terminated_employees


class AWSAudit:

    csv_helper = CsvHelper()
    global terminated_employee_list

    old_csv_header = ['AWS Username', 'Review Decision', 'Rationale', 'Notes', 'Change Required?', 'Date Change Completed']
    old_csv_service_specific_header = ['AWS Username']

    new_csv_header = ['email']

    old_csv_email_key = old_csv_header[0]  # Email column changes for each service in old csv - Hardcode it here
    new_csv_email_key = new_csv_header[0]  # Email column changes for each service in new csv - Hardcode it here

    def check_if_old_user_needs_deprov(self, old_user, new_user_names_set):

        if old_user[self.old_csv_email_key] in terminated_employee_list:
            old_user['Review Decision'] = "Remove Access"
            old_user['Rationale'] = "Terminated / Transferred Employee"
            old_user['Notes'] = "No longer with Pearson"

            if old_user[self.old_csv_email_key] in new_user_names_set:
                old_user['Change Required?'] = "Yes"
            else:
                old_user['Change Required?'] = "No"
        return old_user

    def check_if_new_user_needs_deprov(self, new_user, new_user_names_set):

        if new_user[self.old_csv_email_key] in terminated_employee_list:
            new_user['Review Decision'] = "Remove Access"
            new_user['Rationale'] = "Terminated / Transferred Employee"
            new_user['Notes'] = "No longer with Pearson"
            if new_user[self.old_csv_email_key] in new_user_names_set:
                new_user['Change Required?'] = "Yes"
            else:
                new_user['Change Required?'] = "No"
        return new_user

    def add_default_fields_for_new_user(self, new_user):


        new_user['Review Decision'] = "Access approved"

        if "@" not in new_user[self.old_csv_email_key] or new_user[self.old_csv_email_key] is None or new_user[self.old_csv_email_key] == "":
            new_user['Rationale'] = "Continuing Business Need - Service Account"
            new_user['Notes'] = "Service Account"
        else:
            new_user['Rationale'] = "Continuing Business Need - Developer Account"
            new_user['Notes'] = "Developer"
        new_user['Change Required?']  = ""
        new_user['Date Change Completed'] = ""
        return new_user

    def add_service_specific_fields(self, new_user):

        new_user[self.old_csv_email_key] = new_user.pop(self.new_csv_email_key)  # Replace Email Key in new_user dict with Email Key in old_user key to comply with audit page

        # Add Service Specific Fields Here

        return new_user

    def audit_and_prepare_csv_for_new_users(self, old_user_data, new_user_data):
        old_user_names_set = {person[self.old_csv_email_key] for person in old_user_data}
        new_user_names_set = {person[self.new_csv_email_key] for person in new_user_data}

        for new_user in new_user_data:
            if new_user[self.new_csv_email_key] not in old_user_names_set:
                new_user_with_service_specific_fields = self.add_service_specific_fields(new_user)  # Email Key in new_user dict is replaced to old_csv email key here
                new_user_with_default_fields = self.add_default_fields_for_new_user(new_user_with_service_specific_fields)
                new_user_checked = self.check_if_new_user_needs_deprov(new_user_with_default_fields, new_user_names_set)
                self.csv_helper.write_to_new_csv(new_user_checked, self.old_csv_header)

    def audit_and_prepare_csv_for_old_users(self, old_user_data, new_user_data):
        new_useremail_set = {person[self.new_csv_email_key] for person in new_user_data}

        for old_user in old_user_data:
            if old_user[self.old_csv_email_key] in new_useremail_set:
                old_user_checked = self.check_if_old_user_needs_deprov(old_user, new_useremail_set)
                self.csv_helper.write_to_new_csv(old_user_checked, self.old_csv_header)

    def audit_all_users(self, old_user_data, new_user_data):

        self.audit_and_prepare_csv_for_old_users(old_user_data, new_user_data)
        self.audit_and_prepare_csv_for_new_users(old_user_data, new_user_data)

    def get_value_from_csv(self, csv_path):

        csv_file = open(csv_path, newline=None, mode='r')

        if "old" in csv_path:
            reader = csv.DictReader(csv_file, fieldnames=(self.old_csv_header))
            next(reader)
            old_csv_data = json.dumps([row for row in reader])
            old_csv_data = json.loads(old_csv_data)
            return old_csv_data

        else:
            reader = csv.DictReader(csv_file, fieldnames=(self.new_csv_header))
            next(reader)
            new_csv_data = json.dumps([row for row in reader])
            new_csv_data = json.loads(new_csv_data)
            return new_csv_data


class BitBucketAudit:

    csv_helper = CsvHelper()
    global terminated_employee_list

    old_csv_header =['Full Name', 'Stash Username', 'Email', 'Is Active User', 'Project Access Level', 'Review Decision', 'Rationale', 'Notes', 'Change Required?', 'Date Change Completed']
    old_csv_service_specific_header = ['Full Name', 'Stash Username', 'Email', 'Is Active User', 'Project Access Level']

    new_csv_header = ['DISPLAY NAME', 'USERNAME', 'EMAIL ADDRESS', 'IS ACTIVE', 'PERMISSION']

    old_csv_email_key = old_csv_header[2]  # Email column changes for each service in old csv - Hardcode it here
    new_csv_email_key = new_csv_header[2]  # Email column changes for each service in new csv - Hardcode it here

    def check_if_old_user_needs_deprov(self, old_user, new_user_names_set):

        if old_user[self.old_csv_email_key] in terminated_employee_list:
            old_user['Review Decision'] = "Remove Access"
            old_user['Rationale'] = "Terminated / Transferred Employee"
            old_user['Notes'] = "No longer with Pearson"

            if old_user[self.old_csv_email_key] in new_user_names_set:
                old_user['Change Required?'] = "Yes"
            else:
                old_user['Change Required?'] = "No"
        return old_user

    def check_if_new_user_needs_deprov(self, new_user, new_user_names_set):

        if new_user[self.old_csv_email_key] in terminated_employee_list:
            new_user['Review Decision'] = "Remove Access"
            new_user['Rationale'] = "Terminated / Transferred Employee"
            new_user['Notes'] = "No longer with Pearson"
            if new_user[self.old_csv_email_key] in new_user_names_set:
                new_user['Change Required?'] = "Yes"
            else:
                new_user['Change Required?'] = "No"
        return new_user

    def add_default_fields_for_new_user(self, new_user):


        new_user['Review Decision'] = "Access approved"

        if "@" not in new_user[self.old_csv_email_key] or new_user[self.old_csv_email_key] is None or new_user[self.old_csv_email_key] == "":
            new_user['Rationale'] = "Continuing Business Need - Service Account"
            new_user['Notes'] = "Service Account"
        else:
            new_user['Rationale'] = "Continuing Business Need - Developer Account"
            new_user['Notes'] = "Developer"

        new_user['Change Required?']  = ""
        new_user['Date Change Completed'] = ""

        return new_user

    def add_service_specific_fields(self, new_user):

        new_user[self.old_csv_email_key] = new_user.pop(self.new_csv_email_key)  # Replace Email Key in new_user dict with Email Key in old_user key to comply with audit page

        # old_csv_service_specific_header = ['Full Name', 'Stash Username', 'Email', 'Is Active User',
        #                                    'Project Access Level']
        #
        # new_csv_header = ['DISPLAY NAME', 'USERNAME', 'EMAIL ADDRESS', 'IS ACTIVE', 'PERMISSION']
        # Add Service Specific Fields Here

        new_user['Full Name'] = new_user.pop('DISPLAY NAME')
        new_user['Stash Username'] = new_user.pop('USERNAME')
        new_user['Is Active User'] = new_user.pop('IS ACTIVE')
        new_user['Project Access Level'] = new_user.pop('PERMISSION')

        return new_user

    def audit_and_prepare_csv_for_new_users(self, old_user_data, new_user_data):
        old_user_names_set = {person[self.old_csv_email_key] for person in old_user_data}
        new_user_names_set = {person[self.new_csv_email_key] for person in new_user_data}

        for new_user in new_user_data:
            if new_user[self.new_csv_email_key] not in old_user_names_set:
                new_user_with_service_specific_fields = self.add_service_specific_fields(new_user)  # Email Key in new_user dict is replaced to old_csv email key here
                new_user_with_default_fields = self.add_default_fields_for_new_user(new_user_with_service_specific_fields)
                new_user_checked = self.check_if_new_user_needs_deprov(new_user_with_default_fields, new_user_names_set)
                self.csv_helper.write_to_new_csv(new_user_checked, self.old_csv_header)

    def audit_and_prepare_csv_for_old_users(self, old_user_data, new_user_data):
        new_useremail_set = {person[self.new_csv_email_key] for person in new_user_data}

        for old_user in old_user_data:
            if old_user[self.old_csv_email_key] in new_useremail_set:
                old_user_checked = self.check_if_old_user_needs_deprov(old_user, new_useremail_set)
                self.csv_helper.write_to_new_csv(old_user_checked, self.old_csv_header)

    def audit_all_users(self, old_user_data, new_user_data):

        self.audit_and_prepare_csv_for_old_users(old_user_data, new_user_data)
        self.audit_and_prepare_csv_for_new_users(old_user_data, new_user_data)

    def get_value_from_csv(self, csv_path):

        csv_file = open(csv_path, newline=None, mode='r')

        if "old" in csv_path:
            reader = csv.DictReader(csv_file, fieldnames=(self.old_csv_header))
            next(reader)
            old_csv_data = json.dumps([row for row in reader])
            old_csv_data = json.loads(old_csv_data)
            return old_csv_data

        else:
            reader = csv.DictReader(csv_file, fieldnames=(self.new_csv_header))
            next(reader)
            new_csv_data = json.dumps([row for row in reader])
            new_csv_data = json.loads(new_csv_data)
            return new_csv_data


class ERPSAudit:

    csv_helper = CsvHelper()
    global terminated_employee_list

    old_csv_header =['User Email', 'Review Decision', 'Rationale', 'Notes', 'Change Required?', 'Date Change Completed']
    old_csv_service_specific_header = ['User Email']

    new_csv_header = ['key']

    old_csv_email_key = old_csv_header[0]  # Email column changes for each service in old csv - Hardcode it here
    new_csv_email_key = new_csv_header[0]  # Email column changes for each service in new csv - Hardcode it here

    def check_if_old_user_needs_deprov(self, old_user, new_user_names_set):

        if old_user[self.old_csv_email_key] in terminated_employee_list:
            old_user['Review Decision'] = "Remove Access"
            old_user['Rationale'] = "Terminated / Transferred Employee"
            old_user['Notes'] = "No longer with Pearson"

            if old_user[self.old_csv_email_key] in new_user_names_set:
                old_user['Change Required?'] = "Yes"
            else:
                old_user['Change Required?'] = "No"
        return old_user

    def check_if_new_user_needs_deprov(self, new_user, new_user_names_set):

        if new_user[self.old_csv_email_key] in terminated_employee_list:
            new_user['Review Decision'] = "Remove Access"
            new_user['Rationale'] = "Terminated / Transferred Employee"
            new_user['Notes'] = "No longer with Pearson"
            if new_user[self.old_csv_email_key] in new_user_names_set:
                new_user['Change Required?'] = "Yes"
            else:
                new_user['Change Required?'] = "No"
        return new_user

    def add_default_fields_for_new_user(self, new_user):


        new_user['Review Decision'] = "Access approved"

        if "@" not in new_user[self.old_csv_email_key] or new_user[self.old_csv_email_key] is None or new_user[self.old_csv_email_key] == "":
            new_user['Rationale'] = "Continuing Business Need - Service Account"
            new_user['Notes'] = "Service Account"
        else:
            new_user['Rationale'] = "Continuing Business Need - Developer Account"
            new_user['Notes'] = "Developer"

        new_user['Change Required?']  = ""
        new_user['Date Change Completed'] = ""

        return new_user

    def add_service_specific_fields(self, new_user):

        new_user[self.old_csv_email_key] = new_user.pop(self.new_csv_email_key)  # Replace Email Key in new_user dict with Email Key in old_user key to comply with audit page

        # old_csv_header = ['User Email', 'Review Decision']
        # new_csv_header = ['key']

        return new_user

    def audit_and_prepare_csv_for_new_users(self, old_user_data, new_user_data):
        old_user_names_set = {person[self.old_csv_email_key] for person in old_user_data}
        new_user_names_set = {person[self.new_csv_email_key] for person in new_user_data}

        for new_user in new_user_data:
            if new_user[self.new_csv_email_key] not in old_user_names_set:
                new_user_with_service_specific_fields = self.add_service_specific_fields(new_user)  # Email Key in new_user dict is replaced to old_csv email key here
                new_user_with_default_fields = self.add_default_fields_for_new_user(new_user_with_service_specific_fields)
                new_user_checked = self.check_if_new_user_needs_deprov(new_user_with_default_fields, new_user_names_set)
                self.csv_helper.write_to_new_csv(new_user_checked, self.old_csv_header)

    def audit_and_prepare_csv_for_old_users(self, old_user_data, new_user_data):
        new_useremail_set = {person[self.new_csv_email_key] for person in new_user_data}

        for old_user in old_user_data:
            if old_user[self.old_csv_email_key] in new_useremail_set:
                old_user_checked = self.check_if_old_user_needs_deprov(old_user, new_useremail_set)
                self.csv_helper.write_to_new_csv(old_user_checked, self.old_csv_header)

    def audit_all_users(self, old_user_data, new_user_data):

        self.audit_and_prepare_csv_for_old_users(old_user_data, new_user_data)
        self.audit_and_prepare_csv_for_new_users(old_user_data, new_user_data)

    def get_value_from_csv(self, csv_path):

        csv_file = open(csv_path, newline=None, mode='r')

        if "old" in csv_path:
            reader = csv.DictReader(csv_file, fieldnames=(self.old_csv_header))
            next(reader)
            old_csv_data = json.dumps([row for row in reader])
            old_csv_data = json.loads(old_csv_data)
            return old_csv_data

        else:
            reader = csv.DictReader(csv_file, fieldnames=(self.new_csv_header))
            next(reader)
            new_csv_data = json.dumps([row for row in reader])
            new_csv_data = json.loads(new_csv_data)
            return new_csv_data


class JenkinsAudit:

    csv_helper = CsvHelper()
    global terminated_employee_list

    old_csv_header =['Jenkins Username', 'Full Name', 'Email', 'Review Decision', 'Rationale', 'Notes', 'Change Required?', 'Date Change Completed']
    old_csv_service_specific_header = ['Jenkins Username', 'Full Name', 'Email']

    new_csv_header = ['User_Name', 'Full_Name', 'Email']

    old_csv_email_key = old_csv_header[2]  # Email column changes for each service in old csv - Hardcode it here
    new_csv_email_key = new_csv_header[2]  # Email column changes for each service in new csv - Hardcode it here

    def check_if_old_user_needs_deprov(self, old_user, new_user_names_set):

        if old_user[self.old_csv_email_key] in terminated_employee_list:
            old_user['Review Decision'] = "Remove Access"
            old_user['Rationale'] = "Terminated / Transferred Employee"
            old_user['Notes'] = "No longer with Pearson"

            if old_user[self.old_csv_email_key] in new_user_names_set:
                old_user['Change Required?'] = "Yes"
            else:
                old_user['Change Required?'] = "No"
        return old_user

    def check_if_new_user_needs_deprov(self, new_user, new_user_names_set):

        if new_user[self.old_csv_email_key] in terminated_employee_list:
            new_user['Review Decision'] = "Remove Access"
            new_user['Rationale'] = "Terminated / Transferred Employee"
            new_user['Notes'] = "No longer with Pearson"
            if new_user[self.old_csv_email_key] in new_user_names_set:
                new_user['Change Required?'] = "Yes"
            else:
                new_user['Change Required?'] = "No"
        return new_user

    def add_default_fields_for_new_user(self, new_user):


        new_user['Review Decision'] = "Access approved"

        if "@" not in new_user[self.old_csv_email_key] or new_user[self.old_csv_email_key] is None or new_user[self.old_csv_email_key] == "" or "@pearson.com" not in new_user[self.old_csv_email_key]:
            new_user['Rationale'] = "Continuing Business Need - Service Account"
            new_user['Notes'] = "Service Account"
        else:
            new_user['Rationale'] = "Continuing Business Need - Developer Account"
            new_user['Notes'] = "Developer"

        new_user['Change Required?']  = ""
        new_user['Date Change Completed'] = ""

        return new_user

    def add_service_specific_fields(self, new_user):

        new_user[self.old_csv_email_key] = new_user.pop(self.new_csv_email_key)  # Replace Email Key in new_user dict with Email Key in old_user key to comply with audit page

        # old_csv_service_specific_header = ['Jenkins Username', 'Full Name', 'Email']
        #
        # new_csv_header = ['User_Name', 'Full_Name', 'Email']
        # Add Service Specific Fields Here

        new_user['Jenkins Username'] = new_user.pop('User_Name')
        new_user['Full Name'] = new_user.pop('Full_Name')

        return new_user

    def audit_and_prepare_csv_for_new_users(self, old_user_data, new_user_data):
        old_user_names_set = {person[self.old_csv_email_key] for person in old_user_data}
        new_user_names_set = {person[self.new_csv_email_key] for person in new_user_data}

        for new_user in new_user_data:
            if new_user[self.new_csv_email_key] not in old_user_names_set:
                new_user_with_service_specific_fields = self.add_service_specific_fields(new_user)  # Email Key in new_user dict is replaced to old_csv email key here
                new_user_with_default_fields = self.add_default_fields_for_new_user(new_user_with_service_specific_fields)
                new_user_checked = self.check_if_new_user_needs_deprov(new_user_with_default_fields, new_user_names_set)
                self.csv_helper.write_to_new_csv(new_user_checked, self.old_csv_header)

    def audit_and_prepare_csv_for_old_users(self, old_user_data, new_user_data):
        new_useremail_set = {person[self.new_csv_email_key] for person in new_user_data}

        for old_user in old_user_data:
            if old_user[self.old_csv_email_key] in new_useremail_set:
                old_user_checked = self.check_if_old_user_needs_deprov(old_user, new_useremail_set)
                self.csv_helper.write_to_new_csv(old_user_checked, self.old_csv_header)

    def audit_all_users(self, old_user_data, new_user_data):

        self.audit_and_prepare_csv_for_old_users(old_user_data, new_user_data)
        self.audit_and_prepare_csv_for_new_users(old_user_data, new_user_data)

    def get_value_from_csv(self, csv_path):

        csv_file = open(csv_path, newline=None, mode='r')

        if "old" in csv_path:
            reader = csv.DictReader(csv_file, fieldnames=(self.old_csv_header))
            next(reader)
            old_csv_data = json.dumps([row for row in reader])
            old_csv_data = json.loads(old_csv_data)
            return old_csv_data

        else:
            reader = csv.DictReader(csv_file, fieldnames=(self.new_csv_header))
            next(reader)
            new_csv_data = json.dumps([row for row in reader])
            new_csv_data = json.loads(new_csv_data)
            return new_csv_data

class SonarAudit:

    csv_helper = CsvHelper()
    global terminated_employee_list

    old_csv_header =['USERNAME', 'FULL_NAME', 'EMAIL', 'IS_ACTIVE', 'GROUPS', 'Review Decision', 'Rationale', 'Notes', 'Change Required?', 'Date Change Completed']
    old_csv_service_specific_header = ['USERNAME', 'FULL_NAME', 'EMAIL', 'IS_ACTIVE', 'GROUPS']

    new_csv_header = ['User_Name', 'Full_Name', 'Email']

    old_csv_email_key = old_csv_header[2]  # Email column changes for each service in old csv - Hardcode it here
    new_csv_email_key = new_csv_header[2]  # Email column changes for each service in new csv - Hardcode it here

    def check_if_old_user_needs_deprov(self, old_user, new_user_names_set):

        if old_user[self.old_csv_email_key] in terminated_employee_list:
            old_user['Review Decision'] = "Remove Access"
            old_user['Rationale'] = "Terminated / Transferred Employee"
            old_user['Notes'] = "No longer with Pearson"

            if old_user[self.old_csv_email_key] in new_user_names_set:
                old_user['Change Required?'] = "Yes"
            else:
                old_user['Change Required?'] = "No"
        return old_user

    def check_if_new_user_needs_deprov(self, new_user, new_user_names_set):

        if new_user[self.old_csv_email_key] in terminated_employee_list:
            new_user['Review Decision'] = "Remove Access"
            new_user['Rationale'] = "Terminated / Transferred Employee"
            new_user['Notes'] = "No longer with Pearson"
            if new_user[self.old_csv_email_key] in new_user_names_set:
                new_user['Change Required?'] = "Yes"
            else:
                new_user['Change Required?'] = "No"
        return new_user

    def add_default_fields_for_new_user(self, new_user):


        new_user['Review Decision'] = "Access approved"

        if "@" not in new_user[self.old_csv_email_key] or new_user[self.old_csv_email_key] is None or new_user[self.old_csv_email_key] == "" or "@pearson.com" not in new_user[self.old_csv_email_key]:
            new_user['Rationale'] = "Continuing Business Need - Service Account"
            new_user['Notes'] = "Service Account"
        else:
            new_user['Rationale'] = "Continuing Business Need - Developer Account"
            new_user['Notes'] = "Developer"

        new_user['Change Required?']  = ""
        new_user['Date Change Completed'] = ""

        return new_user

    def add_service_specific_fields(self, new_user):

        new_user[self.old_csv_email_key] = new_user.pop(self.new_csv_email_key)  # Replace Email Key in new_user dict with Email Key in old_user key to comply with audit page

        # old_csv_service_specific_header = ['USERNAME', 'FULL_NAME', 'EMAIL', 'IS_ACTIVE', 'GROUPS']
        # new_csv_header = ['User_Name', 'Full_Name', 'Email']
        # Add Service Specific Fields Here

        new_user['USERNAME'] = new_user.pop('User_Name')
        new_user['FULL_NAME'] = new_user.pop('Full_Name')
        new_user['EMAIL'] = new_user.pop('Email')

        return new_user

    def audit_and_prepare_csv_for_new_users(self, old_user_data, new_user_data):
        old_user_names_set = {person[self.old_csv_email_key] for person in old_user_data}
        new_user_names_set = {person[self.new_csv_email_key] for person in new_user_data}

        for new_user in new_user_data:
            if new_user[self.new_csv_email_key] not in old_user_names_set:
                new_user_with_service_specific_fields = self.add_service_specific_fields(new_user)  # Email Key in new_user dict is replaced to old_csv email key here
                new_user_with_default_fields = self.add_default_fields_for_new_user(new_user_with_service_specific_fields)
                new_user_checked = self.check_if_new_user_needs_deprov(new_user_with_default_fields, new_user_names_set)
                self.csv_helper.write_to_new_csv(new_user_checked, self.old_csv_header)

    def audit_and_prepare_csv_for_old_users(self, old_user_data, new_user_data):
        new_useremail_set = {person[self.new_csv_email_key] for person in new_user_data}

        for old_user in old_user_data:
            if old_user[self.old_csv_email_key] in new_useremail_set:
                old_user_checked = self.check_if_old_user_needs_deprov(old_user, new_useremail_set)
                self.csv_helper.write_to_new_csv(old_user_checked, self.old_csv_header)

    def audit_all_users(self, old_user_data, new_user_data):

        self.audit_and_prepare_csv_for_old_users(old_user_data, new_user_data)
        self.audit_and_prepare_csv_for_new_users(old_user_data, new_user_data)

    def get_value_from_csv(self, csv_path):

        csv_file = open(csv_path, newline=None, mode='r')

        if "old" in csv_path:
            reader = csv.DictReader(csv_file, fieldnames=(self.old_csv_header))
            next(reader)
            old_csv_data = json.dumps([row for row in reader])
            old_csv_data = json.loads(old_csv_data)
            return old_csv_data

        else:
            reader = csv.DictReader(csv_file, fieldnames=(self.new_csv_header))
            next(reader)
            new_csv_data = json.dumps([row for row in reader])
            new_csv_data = json.loads(new_csv_data)
            return new_csv_data


def setup_argparser():

    parser = argparse.ArgumentParser(description="Pass in the old_csv (sheet from previous user audit workbook) and new_csv and the script will generate a new csv with audited users")

    parser.add_argument('--service_type',
                        choices=['jenkins', 'zabbix', 'erps', 'bitbucket', 'sonar', 'aws'],
                        help='Specify the service which is being audited.',
                        required=True)

    parser.add_argument('--old_csv',
                        help="Pass the service's last quarter's audit sheet",
                        required=True)

    parser.add_argument('--new_csv',
                        help="Pass the service's new users csv file obtained by running user-audit.sh",
                        required=True)

    parser.add_argument('--terminated_employee_csv',
                        help="Pass the service's new users csv file obtained by running user-audit.sh",
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

    # Setup CSV writer helper object - to write to csv after user-audit
    csv_name = "".join(("".join(args.new_csv.split("/")[-1:])).split(".")[0])  # Get only csv name from absolute csv path
    CsvHelper.get_csv_helper(CsvHelper, csv_name)

    # Get and Set Terminated Employee List - used while user-audit - This file is generated by fusion-directory-service
    global terminated_employee_list
    terminated_employee_list = TerminatedEmployee.get_all_terminated_users_csv(TerminatedEmployee, args.terminated_employee_csv)

    # Audit
    if args.service_type == 'aws':
        awsAuditor = AWSAudit()
        old_user_data = awsAuditor.get_value_from_csv(args.old_csv)
        new_user_data = awsAuditor.get_value_from_csv(args.new_csv)
        awsAuditor.audit_all_users(old_user_data, new_user_data)

    elif args.service_type == 'bitbucket':
        bitbucketAuditor = BitBucketAudit()
        old_user_data = bitbucketAuditor.get_value_from_csv(args.old_csv)
        new_user_data = bitbucketAuditor.get_value_from_csv(args.new_csv)
        bitbucketAuditor.audit_all_users(old_user_data, new_user_data)

    elif args.service_type == 'erps':
        erpsAuditor = ERPSAudit()
        old_user_data = erpsAuditor.get_value_from_csv(args.old_csv)
        new_user_data = erpsAuditor.get_value_from_csv(args.new_csv)
        erpsAuditor.audit_all_users(old_user_data, new_user_data)

    elif args.service_type == 'jenkins':
        jenkinsAuditor = JenkinsAudit()
        old_user_data = jenkinsAuditor.get_value_from_csv(args.old_csv)
        new_user_data = jenkinsAuditor.get_value_from_csv(args.new_csv)
        jenkinsAuditor.audit_all_users(old_user_data, new_user_data)

    elif args.service_type == 'sonar':
        sonarAuditor = SonarAudit()
        old_user_data = sonarAuditor.get_value_from_csv(args.old_csv)
        new_user_data = sonarAuditor.get_value_from_csv(args.new_csv)
        sonarAuditor.audit_all_users(old_user_data, new_user_data)


if __name__ == "__main__":
    main()