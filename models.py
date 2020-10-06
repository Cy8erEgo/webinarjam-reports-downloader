import os
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, JavascriptException

from exceptions import NoDataException, NoMoreWebinarsException


SITE_URL = "https://app.webinarjam.com/my-registrants"


def try_until_it_works(func):
    def wrapper(*args, **kwargs):
        for i in range(1, 8):
            try:
                print(f"Attempt {i}")
                func(*args, **kwargs)
                return
            except TimeoutException:
                pass
    return wrapper


class WebinarjamController:
    def __init__(self, login, password, headless=True, logger=None):
        self._reports_dir = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "reports"
        )
        self._logger = logger

        # start a browser
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        prefs = {"download.default_directory": self._reports_dir}
        if headless:
            options.add_argument("--headless")
        options.add_experimental_option("prefs", prefs)

        self._driver = webdriver.Chrome(chrome_options=options)
        self._driver.maximize_window()
        self.open = self._driver.get

        # login
        self.login(login, password)

    def close(self):
        self._driver.close()

    def get_reports_cnt(self):
        return len(os.listdir(self._reports_dir))

    def _open_in_new_tab(self, url):
        """
        Creates a new tab and switches context to it
        """
        # create a new tab
        self._driver.execute_script("window.open()")

        # switch context to it
        self._driver.switch_to.window(self._driver.window_handles[-1])

        # open the url
        self.open(url)

    def _close_tab(self):
        """
        Closes active tab
        """
        self._driver.execute_script("window.close();")
        sleep(1)
        self._driver.switch_to.window(self._driver.window_handles[-1])

    def _close_modal(self):
        modal_el = self._driver.find_elements_by_class_name("modal-content")[-1]
        modal_el.find_elements_by_css_selector("button.close")[-1].click()
        WebDriverWait(self._driver, 5).until(
            ec.invisibility_of_element_located(modal_el)
    )

    def login(self, login, password):
        self.open(SITE_URL)

        login_el = WebDriverWait(self._driver, 10).until(
            ec.presence_of_element_located((By.CSS_SELECTOR, "input#email"))
        )
        passwd_el = self._driver.find_element_by_css_selector("input#password")

        login_el.send_keys(login)
        passwd_el.send_keys(password)
        passwd_el.send_keys(Keys.ENTER)

        self.open("https://app.webinarjam.com/app/ew")

        # wait for loading
        try:
            WebDriverWait(self._driver, 15).until(
                ec.visibility_of_element_located((By.CSS_SELECTOR, "a.nav-link"))
            )
        except TimeoutException:
            # probably threw back, attempt to click
            # select "EverWebinar"
            second_choice_el = WebDriverWait(self._driver, 15).until(
                ec.visibility_of_element_located(
                    (By.XPATH, './/a[contains(text(), "Access")]')
                )
            )
            second_choice_el.click()

    def apply_filter(self, webinar_index, event_index):
        def select_option(filter_el, index):
            filter_el.find_element_by_tag_name("button").click()

            # wait for the dropdown to appear
            WebDriverWait(self._driver, 10).until(
                ec.visibility_of_element_located(
                    (By.CLASS_NAME, "v-dropdown-container")
                )
            )

            # select some option
            self._driver.execute_script(
                f'document.querySelectorAll(".v-dropdown-item")[{index}].click()'
            )

        (
            webinar_filter_el,
            session_filter_el,
            event_filter_el,
        ) = self._driver.find_elements_by_xpath(
            '//div[@class="col-4"]/div[contains(@class, "form-group")]'
        )[:3]

        # SELECT WEBINAR
        try:
            select_option(webinar_filter_el, webinar_index)
        except JavascriptException:
            raise NoMoreWebinarsException

        # SELECT SESSION
        select_option(session_filter_el, 1)

        # SELECT EVENT
        select_option(event_filter_el, event_index)

        # click GO button
        btn_go_el = self._driver.find_element_by_css_selector("button#go")
        btn_go_el.click()

        # wait a little bit
        try:
            WebDriverWait(self._driver, 15).until(
                ec.visibility_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
        except TimeoutException:
            # no data, possibly
            raise NoDataException

    @try_until_it_works
    def get_report_by_webinar(self, webinar_index, event_index):
        # apply filter
        try:
            self.apply_filter(webinar_index, event_index)
        except NoDataException:
            return

        # export
        btn_export_el_1 = self._driver.find_element_by_xpath(
            '//span/button[contains(text(), "Export")]'
        )
        btn_export_el_1.click()

        # wait for the modal window to appear
        # TODO
        pass

        # click on "Export the currently selected filters"
        self._driver.execute_script(
            'document.querySelector("input#export_option_1").click()'
        )

        WebDriverWait(self._driver, 10).until(
            ec.element_to_be_clickable(
                (
                    By.XPATH,
                    '//button[contains(@class, "btn-success") and contains(text(), "Export")]',
                )
            )
        )

        # click on "Export"
        modal_el = self._driver.find_elements_by_class_name("modal-content")[-1]
        reports_cnt_start = self.get_reports_cnt()

        try:
            self._driver.execute_script(
                "document.querySelectorAll('.modal-content button.btn-success')[3].click()"
            )
            # wait for the report to download
            WebDriverWait(self._driver, 60).until(
                ec.invisibility_of_element_located(modal_el)
            )
            while self.get_reports_cnt() == reports_cnt_start:
                sleep(1)
        except TimeoutException:
            self._close_modal()
            raise

    def get_all_reports(self, event: str):
        """
        Get a list of reports for all webinars
        """
        event_map = {
            "all time": 1,
            "today": 2,
            "yesterday": 3,
            "this week": 4,
            "last week": 5,
            "last 7 days": 6,
            "this month": 7,
            "last month": 8,
            "last 30 days": 9,
        }
        event_index = event_map[event]

        try:
            # go to the report creation page
            self.open(SITE_URL)

            # wait for loading
            WebDriverWait(self._driver, 15).until(
                ec.visibility_of_element_located(
                    (By.XPATH, '//h3[contains(text(), "active registrants")]')
                )
            )

            for webinar_index in range(1, 100):
                self._logger.info(f"step 1: downloading the report #{webinar_index}...")
                try:
                    self.get_report_by_webinar(webinar_index, event_index)
                except NoMoreWebinarsException:
                    self._logger.info("end of webinar list reached")
                    break
        finally:
            self.close()
