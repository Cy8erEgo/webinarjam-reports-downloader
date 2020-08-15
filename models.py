import os
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from config import *


class BrowserActions:
    pass


class WebinarjamController:
    def __init__(self):
        self._reports_dir = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "reports"
        )

        # start a browser
        options = webdriver.ChromeOptions()
        prefs = {"download.default_directory": self._reports_dir}
        options.add_experimental_option("prefs", prefs)

        self._driver = webdriver.Chrome(chrome_options=options)
        self._driver.maximize_window()
        self.open = self._driver.get

        # login
        self.login()

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
        # TODO: sleep maybe?
        sleep(1)
        self._driver.switch_to.window(self._driver.window_handles[-1])

    def login(self):
        self.open(SITE_URL)

        login_el = WebDriverWait(self._driver, 10).until(
            ec.presence_of_element_located((By.CSS_SELECTOR, "input#email"))
        )
        passwd_el = self._driver.find_element_by_css_selector("input#password")
        submit_el = self._driver.find_element_by_css_selector("button")

        login_el.send_keys(SITE_LOGIN)
        passwd_el.send_keys(SITE_PASSWD)
        passwd_el.send_keys(Keys.ENTER)

        # select "EverWebinar"
        second_choice_el = WebDriverWait(self._driver, 15).until(
            ec.visibility_of_element_located(
                (By.XPATH, './/a[contains(text(), "Access")]')
            )
        )

        # кликнуть по кнопку почему-то не выходит
        # second_choice_el.click()

        self.open("https://app.webinarjam.com/app/ew")
        # TODO: здесь переиодически возникает затык: переадресует обратнно в /home

        # # wait for loading
        WebDriverWait(self._driver, 15).until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, "a.nav-link"))
        )

    def apply_filter(self):
        def select_option(filter_el, index):
            filter_el.find_element_by_tag_name("button").click()

            # wait for the dropdown to appear
            dropdown_container_el = WebDriverWait(self._driver, 10).until(
                ec.visibility_of_element_located(
                    (By.CLASS_NAME, "v-dropdown-container")
                )
            )
            dropdown_items = dropdown_container_el.find_elements_by_class_name(
                "v-dropdown-item"
            )

            # select the first option
            self._driver.execute_script(
                f'document.querySelectorAll(".v-dropdown-item")[{index}].click()'
            )
            # webinar_filter_el.find_element_by_tag_name("button").click()

        # должен быть на странице с фильтром
        (
            webinar_filter_el,
            session_filter_el,
            event_filter_el,
        ) = self._driver.find_elements_by_xpath(
            '//div[@class="col-4"]/div[contains(@class, "form-group")]'
        )

        # SELECT WEBINAR
        select_option(webinar_filter_el, 1)
        # webinar_filter_el.find_element_by_tag_name("button").click()

        # wait for the dropdown to appear
        # dropdown_container_el = WebDriverWait(self._driver, 10).until(ec.visibility_of_element_located((By.CLASS_NAME, "v-dropdown-container")))
        # dropdown_items = dropdown_container_el.find_elements_by_class_name("v-dropdown-item")

        # select the first option
        # for i in range(1, len(dropdown_items))[:1]:  # TODO: fix :1
        #     self._driver.execute_script(f'document.querySelectorAll(".v-dropdown-item")[{i}].click()')
        #     webinar_filter_el.find_element_by_tag_name("button").click()

        # SELECT SESSION
        select_option(session_filter_el, 1)

        # SELECT EVENT
        select_option(event_filter_el, 3)

        # click GO button
        btn_go_el = self._driver.find_element_by_css_selector("button#go")
        btn_go_el.click()

        # wait a little bit
        WebDriverWait(self._driver, 15).until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, "table.table"))
        )

    def get_report(self):
        # должен быть авторизован
        # TODO: избавиться от хардкода

        # go to the report creation page
        self.open("https://app.webinarjam.com/my-registrants")

        # wait for loading
        WebDriverWait(self._driver, 15).until(
            ec.visibility_of_element_located(
                (By.XPATH, '//h3[contains(text(), "active registrants")]')
            )
        )

        # apply filter
        self.apply_filter()

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
        def get_reports_cnt():
            return len(os.listdir(self._reports_dir))

        reports_cnt_start = get_reports_cnt()

        self._driver.execute_script("document.querySelectorAll('.modal-content button.btn-success')[3].click()")

        # wait for the report to download
        modal_el = self._driver.find_elements_by_class_name("modal-content")[-1]
        WebDriverWait(self._driver, 60).until(
            ec.invisibility_of_element_located(modal_el)
        )

        while get_reports_cnt() == reports_cnt_start:
            sleep(1)
