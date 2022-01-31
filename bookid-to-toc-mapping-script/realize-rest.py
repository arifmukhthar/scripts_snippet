from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromeDriverConfig
import logging
import argparse
import requests
import json


class ChromeDriver:

    __chrome_driver = None
    chrome_mode = str

    def get_chrome_driver_instance(self):

        # Chrome driver properties
        bin_location = chromeDriverConfig.chromeDriver['BIN_LOCATION']
        exec_path = chromeDriverConfig.chromeDriver['EXEC_PATH']

        if ChromeDriver.__chrome_driver is None:
            options = webdriver.ChromeOptions()
            options.binary_location = bin_location
            options.add_argument('window-size=800x841')
            if self.chrome_mode == 'headless':
                options.add_argument(self.chrome_mode)
            ChromeDriver.__chrome_driver = webdriver.Chrome(executable_path=exec_path, chrome_options=options)
            logging.info("Initialized Chrome Instance in '{}' Mode".format(self.chrome_mode))
        return ChromeDriver.__chrome_driver


class LoginService:

    def login_to_rumba(self, realize_admin_username, realize_admin_password, realize_environment):

        # Initializing Chrome Driver instance
        self.driver = ChromeDriver().get_chrome_driver_instance()
        logging.info("Initializing Chrome Driver instance for login activities")

        # Set Properties from configs file for login
        username = realize_admin_username
        password = realize_admin_password

        # Set CSS_Selector of Box and Button in login page
        username_box = "input#username"
        password_box = "input#password"
        sign_in_button = "button.btn-submit"
        realize_home_page_element = "div div div div ul li a i.icon-search"

        # Set url based on env
        if realize_environment == "NIGHTLY":
            url = chromeDriverConfig.realizeURL['NIGHTLY']
        elif realize_environment == "PRODUCTION":
            url = chromeDriverConfig.realizeURL['PRODUCTION']

        logging.info("Trying to login to '{}'".format(url))

        self.driver.get(url)
        try:
            logging.info("Entering user credentials into Rumba Login Page")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, username_box)))
            logging.info("Entering Username")
            self.driver.find_element_by_css_selector(username_box).send_keys(username)
        except Exception:
            logging.info("Error while entering username into username box")

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, password_box)))
            logging.info("Entering Password")
            self.driver.find_element_by_css_selector(password_box).send_keys(password)
        except Exception:
            logging.info("Error while entering password into password box")

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sign_in_button)))
            logging.info("Found Sign in button - Clicking")
            self.driver.find_element_by_css_selector(sign_in_button).click()
        except Exception:
            logging.info("Error while clicking submit button in Rumba Login Page")

        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, realize_home_page_element)))
            logging.info("Found Realize Home Page")
        except Exception:
            logging.info("Cannot find Realize Home Page. Failed login to realize, Probably because the Realize username/password were invalid.Please verify you have the right credentials and re-run the job.")
            exit(1)

        return self.driver.get_cookies()

    def get_jsession_from_cookies(self, cookies):

        for cookie in cookies:
            if cookie['name'] == 'JSESSIONID':
                logging.info("Found JSESSION ID")
                return cookie['value']
            else:
                logging.info("JSESSION ID not found in Cookie: '{}', moving on to other cookies".format(cookie['name']))


class RestCallService:

    def get_realize_metadata_api_endpoint(self, realize_environment):

        # Set url based on env
        if realize_environment == "NIGHTLY":
            url = chromeDriverConfig.realizeApiEndpoint['NIGHTLY']
        elif realize_environment == "PRODUCTION":
            url = chromeDriverConfig.realizeApiEndpoint['PRODUCTION']

        return url

    def check_if_toc_url_already_mapped(self, response):
        warning_message = "Warning : TOC Url should not be mapped to more than one bookId"
        try:
            if warning_message in response.text:
                return True
        except Exception as e:
            return False

        return False
    def validate_response(self, response, book_id):

        if response.status_code is not 200:
            response_json = json.loads(response._content)
            logging.info("Book ID: '{}' - BookId to TOC mapping failed with error code '{}', error message '{}' and response code '{}'"
                         .format(book_id, response_json['errorCode'], response_json['errorMessage'], response.status_code))
            exit(1)

        toc_reused = self.check_if_toc_url_already_mapped(response)

        if toc_reused:
            logging.info(response.text)
            exit(0)

        logging.info("Book ID: '{}' - BookId to TOC mapping complete with response code '{}'".format(book_id, response.status_code))

    def make_post_request(self, jsession_id, realize_environment, book_id, book_metadata_key, book_metadata_value):

        payload = {'bookId': book_id, 'bookMetadataKey': book_metadata_key, 'bookMetadataValue': book_metadata_value}
        cookies = {'JSESSIONID': jsession_id}
        headers = {'content-type': 'application/x-www-form-urlencoded'}

        metadata_api_endpoint_url = self.get_realize_metadata_api_endpoint(realize_environment)
        
        logging.info("Making POST call to Realize-{} for mapping Book Id and toc for Book: '{}'".format(realize_environment, book_id))

        api_request = requests.post(metadata_api_endpoint_url, params=payload, cookies=cookies, headers=headers)

        return api_request


def setup_argparser():

    parser = argparse.ArgumentParser(
        description="Pass in username and password for Realize Enivironment being accessed")

    parser.add_argument('--username',
                        help="Key in admin username",
                        required=True)

    parser.add_argument('--password',
                        help="Key in admin password",
                        required=True)

    parser.add_argument('--environment',
                        choices=['NIGHTLY', 'PRODUCTION'],
                        help='Specify the environment to map book-id-to-toc. `Night` or `Production`',
                        required=True)

    parser.add_argument('--book_id',
                        help="Key in book_id",
                        required=True)

    parser.add_argument('--book_metadata_key',
                        help="Key in book_metadata_key. DEFAULT is `toc`", default='toc',
                        required=False)

    parser.add_argument('--book_metadata_value',
                        help="Key in book_metadata_value",
                        required=True)

    parser.add_argument('--chrome_mode',
                        choices=['gui', 'headless'],
                        help='Specify the mode to run chrome driver. `gui` or `headless` DEFAULT is `headless`',
                        default='headless',
                        required=False)

    parser.add_argument('--logging_level',
                        choices=['debug', 'info'],
                        help="Specify the logging level and monitor peopledata.log file. /n Use 'debug' level for Selinium level debugging. \n DEFAULT is INFO. ",
                        default="info",
                        required=False)

    return parser.parse_args()


def setup_logging(logging_level):
    if logging_level == 'debug':
        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')

def main():

    # Setup argparser
    args = setup_argparser()

    # Setup logging
    setup_logging(args.logging_level)

    # Initialize chrome driver - Singleton class - only creates one instance of chrome driver
    driver = ChromeDriver()
    driver.chrome_mode = args.chrome_mode
    driver.get_chrome_driver_instance()

    # Login in to Realize and get jsession id to make post calls later
    login_service = LoginService()
    cookies = LoginService.login_to_rumba(login_service, args.username, args.password, args.environment)
    jsession_id = LoginService.get_jsession_from_cookies(login_service, cookies)

    # Print Arguments
    logging.info("\n Realize Environment: '{}' \n Realize Username: '{}' \n Book ID: '{}' \n "
                 "Book Metadata Key: '{}' \n Book Metadata Value: '{}'".format(args.environment,
                                                                               args.username,
                                                                               args.book_id, args.book_metadata_key,
                                                                               args.book_metadata_value))

    # Make POST call to Realize to  and validate response
    response = RestCallService().make_post_request(jsession_id, args.environment, args.book_id, args.book_metadata_key, args.book_metadata_value)

    logging.info("Checking if POST call to Realize-{} for mapping Book Id and toc for BOOK_ID: '{}' was successful?".format(args.environment, args.book_id))
    RestCallService().validate_response(response, args.book_id)


if __name__ == "__main__":
    main()
