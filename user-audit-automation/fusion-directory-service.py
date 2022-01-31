from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import FusionDirectoryConfigs
import pyotp
import csv
import logging
import argparse
import time
import os


class ChromeDriver:

    __chrome_driver = None
    chrome_mode = str

    def get_chrome_driver_instance(self):

        # Chrome driver properties
        bin_location = FusionDirectoryConfigs.chromeDriver['BIN_LOCATION']
        exec_path = FusionDirectoryConfigs.chromeDriver['EXEC_PATH']

        if ChromeDriver.__chrome_driver is None:
            options = webdriver.ChromeOptions()
            options.binary_location = bin_location
            options.add_argument('window-size=800x841')
            if self.chrome_mode == 'headless':
                options.add_argument(self.chrome_mode)
            ChromeDriver.__chrome_driver = webdriver.Chrome(executable_path=exec_path, chrome_options=options)
            logging.info("Initialized Chrome Instance in '{}' Mode".format(self.chrome_mode))
        return ChromeDriver.__chrome_driver


class CsvService:

    def check_if_file_exists(self, sheet):
        cwd = os.getcwd()
        file_exists = os.path.isfile('{}/{}'.format(cwd, sheet))
        return file_exists

    def get_all_users_name_from_csv(self, csv_directory):

        all_username_list = list()

        with open(csv_directory, mode='r') as csv_file:
            reader = csv.reader(csv_file)

            next(reader)
            for row in reader:
                all_username_list.append(row[0])

        return all_username_list

    def write_all_user_name_to_csv(self, terminated_employee_list):

        sheet = "terminated_employees.csv"
        file_exists = self.check_if_file_exists(sheet)

        with open(sheet, mode='a') as useremail_sheet:
            terminated_employees_file = csv.DictWriter(useremail_sheet, fieldnames=["Email"])

            if not file_exists:
                terminated_employees_file.writeheader()
            for user_email in terminated_employee_list:
                terminated_employees_file.writerow({'Email': user_email})


class LoginService:

    # Set Properties from configs file for login
    url = FusionDirectoryConfigs.Fusion_Directory_URL
    mfa_secret = FusionDirectoryConfigs.credentials['MFA_SECRET']
    username = FusionDirectoryConfigs.credentials['USERNAME']
    password = FusionDirectoryConfigs.credentials['PASSWORD']

    def __init__(self):

        # Initialize Chrome Driver
        self.driver = ChromeDriver().get_chrome_driver_instance()
        logging.info("Reusing already Initialized Chrome Driver for login activites")

    def sign_in_page(self, url, username, password):

        logging.info("In Sign in page")
        self.driver.get(url)

        logging.info("Finding username box and entering username")
        self.driver.find_element_by_id('user-name-txt').send_keys(username)

        logging.info("Finding password box and entering password")
        self.driver.find_element_by_id('pwd-txt').send_keys(password)

        logging.info("Click sign in button")
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, 'signin-button')))
        finally:
            self.driver.find_element_by_id('signin-button').click()

    def calculate_otp(self):

        # Initialize OTP generator
        logging.info("Initializing OTP Generator")
        self.totp = pyotp.TOTP(self.mfa_secret)

        current_otp = self.totp.now()
        logging.info("Generating and returning current OTP to enter into MFA page {}".format(current_otp))
        return current_otp

    def mfa_page(self):

        logging.info("Navigated to MFA Page")

        # Find 'security by code' button
        try:
            logging.info("Find MFA button on page and wait till its available to click()")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="root-container"]/div[3]/button')))
        finally:
            logging.info("Found MFA button and clicking on it")
            self.driver.find_element_by_xpath('//*[@id="root-container"]/div[3]/button').click()
            logging.info("Clicked on mfa button")

        # Generate OTP and enter the code
        current_otp = self.calculate_otp()

        logging.info("Entering OTP {} in OTP box".format(current_otp))
        self.driver.find_element_by_id('otp-txt').send_keys(current_otp)

        logging.info("Clicking OTP confirm button")
        self.driver.find_element_by_xpath('//*[@id="root-container"]/form/div/div/div').click()

    def login_to_mycloud(self):

        logging.info("*** STARTING SIGN IN TO myCloud WITH USER CREDENTIALS and OPENING FUSION DIRECTORY ***")
        self.sign_in_page(self.url, self.username, self.password)

        logging.info("*** STARTING MFA SIGN IN ***")
        self.mfa_page()


class DirectoryService:

    # CSS_Selector of Search Boxes and Search Buttons in Home page and in-application page of Fusion Directory
    # These Selectors are used in the script to find elements in the page
    home_directory_search_box_selector = "table input"
    inapp_directory_search_box_selector = "table input"
    home_directory_search_button_selector = "table[summary] a[title='Search']"
    inapp_directory_search_button_selector = "button[title='Search']"

    terminated_employee_email_list = list()

    def __init__(self):

        # Use existing chrome driver
        self.driver = ChromeDriver().get_chrome_driver_instance()
        logging.info("Reusing already Initialized Chrome Driver for Fusion Directory Service Activities")

    def check_directory_search_button(self):
        search_button = None

        logging.info("Searching for Search Button's Selector ID")

        # Checking Directory page to find search button element
        try:
            logging.info("Checking if inapp Search Button is found in the current page")
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.inapp_directory_search_button_selector)))
            search_button = self.inapp_directory_search_button_selector
            logging.info("Found inapp Search Button in the current page - Using inapp Search Button")

        except Exception:
            logging.info("Inapp Search Button not found in the current page - Continuing to check if Home Page Search Button is found")
            try:
                logging.info("Checking if Home Page Search Button is found in the current page")
                WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.home_directory_search_button_selector)))
                search_button = self.home_directory_search_button_selector
                logging.info("Found Home Page Search Button in the current page - Using Home Search Button")

            except Exception:
                logging.error("Search Button not found - There is a problem - Please check screenshot saved at {}".format(os.getcwd()))
                self.driver.save_screenshot('{}/Selenium-Useraudit.png'.format(os.getcwd()))

        return search_button

    def check_directory_search_box(self):

        search_box = None

        logging.info("Searching for Home Page Search Box's Selector ID")

        # checking Directory page to find search box element
        try:
            logging.info("Checking if Home Page Search Box is found in the current page")
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.home_directory_search_box_selector)))
            search_box = self.home_directory_search_box_selector
            logging.info("Found Home Page Search Box in the current page - Using Home Page Search Box")

        except Exception:
            logging.info("Home Page Search Box not found in the current page - Continuing to check if inapp Search Box is found")
            try:
                logging.info("Checking if inapp Page Search Box is found in the current page")
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.inapp_directory_search_box_selector)))
                search_box = self.inapp_directory_search_box_selector
                logging.info("Found inapp Search Button in the current page - Using inapp Search Box")
            except Exception:
                logging.error(
                    "Search Box not found - There is a problem - Please check screenshot saved at {}".format(
                        os.getcwd()))
                self.driver.save_screenshot('{}/Selenium-Useraudit.png'.format(os.getcwd()))
        return search_box

    def setup_search_page(self, search_box, search_button):

        # Pre-flight checks - Navigating to the default search page so that script doesn't need to search for search_box and search_button everytime

        logging.info("Setting up Search Page - One time setup to imporove code performance")
        try:
            logging.info("Setting up Search Page - Waiting for Search Box in Search Page")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, search_box)))
        finally:
            logging.info("Setting up Search Page - Entering test value")
            self.driver.find_element_by_css_selector(search_box).send_keys('Arif')

        self.driver.find_element_by_css_selector(search_button).click()
        logging.info("Setting up Search Page - Entered Test value anf Search page is Setup")

    def start_directory_service(self):

        # Setup a default search page so that script doesn't need to search for search_box and search_button everytime
        logging.info("*** STARTING DIRECTORY SERVICE ***")
        self.setup_search_page(self.check_directory_search_box(), self.check_directory_search_button())

    def enter_email_and_search(self, email, search_box, search_button):

        # Clear Search Box, enter user's email and search
        try:
            logging.info("Checking if Search Box is present")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, search_box)))
        except Exception:
            logging.error(
                "Search Box not found - There is a problem - Please check screenshot saved at {}".format(
                    os.getcwd()))
            self.driver.save_screenshot('{}/Selenium-Useraudit.png'.format(os.getcwd()))
        finally:
            logging.info("Clearing Search Box and entering '{}'".format(email))
            self.driver.find_element_by_css_selector(search_box).clear()
            self.driver.find_element_by_css_selector(search_box).send_keys(email)
            logging.info("Entered value '{}' in  Search Box".format(email))

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, search_button)))

        finally:
            self.driver.find_element_by_css_selector(search_button).click()
            logging.info("Clicked Search button with value '{}' in Search Box".format(email))
            logging.info("Sleeping for 3 Seconds to wait for values to load")
            time.sleep(3)

        try:
            user_email = getattr(WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                "[summary='Search Results'] tbody tr td span div a[href*='mailto:']"))),
                'text').lower()

            if user_email == email:
                logging.info("Email exists in Fusion Directory - Employee still works with Pearson".format(email))
                logging.info("*** MOVING ON TO NEXT EMPLOYEE ***")

        except Exception:
            logging.info("{} Email not found in Fusion Directory - Looks like User left Pearson".format(email))
            return email

    def check_if_employees_exists(self, name_sheet):

        # Get email list of all employees currently using our services
        logging.info("Get users email from the csv provided")
        self.employee_email_list = CsvService.get_all_users_name_from_csv(CsvService, name_sheet)

        # Find and set search box and search button elements
        logging.info("Check and Setup Search Box and Search Button")
        search_box = self.check_directory_search_box()
        search_button = self.check_directory_search_button()

        for email in self.employee_email_list:
            logging.info("*** CHECKING IF {} IS IN FUSION DIRECTORY ***".format(email))

            terminated_employee_email = self.enter_email_and_search(email, search_box, search_button)
            if terminated_employee_email is not None and not "":
                logging.info("Adding {} to Terminated Employees List".format(terminated_employee_email))
                self.terminated_employee_email_list.append(terminated_employee_email)
                logging.info("*** MOVING ON TO NEXT EMPLOYEE ***")

        logging.info("Checked Directory for all email ids in the provided csv - returning terminated employee list to be written to a csv")
        return self.terminated_employee_email_list


def setup_argparser():

    parser = argparse.ArgumentParser(description="Pass in a csv file with user's email and the scripts outputs a csv with email's of users who are no loger with the company")

    parser.add_argument('--users_email_csv',
                        help="1. Pass in a CSV with all user's email.",
                        required=True)

    parser.add_argument('--chrome_mode',
                        choices=['gui', 'headless'],
                        help='Specify the mode Selinium should run Chrome Driver. \n 1. gui - with chrome gui (Chrome Browser GUI opens in Foreground) OR \n 2. headless - without chrome gui (Chrome Browser runs without GUI in background). \n DEFAULT is GUI',
                        default='gui',
                        required=False)

    parser.add_argument('--logging_level',
                        choices=['debug', 'info'],
                        help="Specify the logging level and monitor peopledata.log file. /n Use 'debug' level for Selinium level debugging. \n DEFAULT is INFO. ",
                        default="info",
                        required=False)

    return parser.parse_args()


def setup_logging(logging_level):

    if logging_level == 'debug':
        logging.basicConfig(level=logging.DEBUG, filename='rfaudit.log', filemode='a',
                            format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')
    else:
        logging.basicConfig(level=logging.INFO, filename='rfaudit.log', filemode='a',
                            format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')


def main():

    # Setup argparser
    args = setup_argparser()

    # Setup logging
    setup_logging(args.logging_level)

    # Initialize chrome driver - Singleton class only creates one instance of chrome driver
    driver = ChromeDriver()
    driver.chrome_mode = args.chrome_mode
    driver.get_chrome_driver_instance()

    # Login in to Fusion Directory
    LoginService().login_to_mycloud()

    # Setup Directory Search Page - One Time process to improve code performance
    DirectoryService().start_directory_service()
    time.sleep(5)

    # Check if employees in the CSV are still with Pearson
    terminated_employee_list = DirectoryService().check_if_employees_exists(args.users_email_csv)

    # Write Terminated User's Email to a new csv
    CsvService.write_all_user_name_to_csv(CsvService(), terminated_employee_list=terminated_employee_list)


if __name__ == "__main__":
    main()