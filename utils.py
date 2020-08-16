import os
import csv
from typing import List
from contextlib import closing
import logging

import pymysql.cursors


REPORTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "reports")


def get_registrants_from_csv() -> List[List]:
    """
    Receives a list of registrants from reports
    """
    registrants = []
    for report_name in os.listdir(REPORTS_DIR):
        with open(os.path.join(REPORTS_DIR, report_name), newline="") as report_csv:
            report_registrants = list(csv.DictReader(report_csv))[1:]
            registrants.extend(report_registrants)
    return registrants


def write_registrants_to_db(registrants: list, db_host: str, db_login: str, db_pass: str, db_name: str) -> None:
    params = {
        "host": db_host,
        "user": db_login,
        "password": db_pass,
        "db": db_name,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }
    s = ", ".join(["%s"] * 25)
    fields = ", ".join(
        (
            "first_name",
            "last_name",
            "phone_country_code",
            "phone_number",
            "email",
            "ip",
            "webinar",
            "session",
            "event",
            "registration_date",
            "attended_live",
            "attended_live_date",
            "time_to_enter_live_room",
            "time_in_live_room",
            "purchased_from_live_room",
            "revenue_from_live_room",
            "watched_replay",
            "watched_replay_date",
            "time_in_replay_room",
            "purchased_from_replay_room",
            "revenue_from_replay_room",
            "gdrp_status",
            "gdrp_communications",
            "gdrp_date",
            "gdrp_ip",
        )
    )
    with closing(pymysql.connect(**params)) as connection:
        for registrant in registrants:
            # check if there is a such registrant
            with connection.cursor() as cursor:
                query = (
                    'SELECT id FROM registrants WHERE email = "%s" and webinar = "%s" and session = "%s" and '
                    'event = "%s" and attended_live_date = "%s" and time_to_enter_live_room = "%s" and gdrp_date = "%s"'
                    % (
                        registrant["Email"],
                        registrant["Webinar"],
                        registrant["Session"],
                        registrant["Event"],
                        registrant["Attended live date"],
                        registrant["Time to enter live room"],
                        registrant["GDPR date"]
                    )
                )

                cursor.execute(query)
                result = cursor.fetchall()

            # if such a registrant already exists, skip
            if result:
                continue

            # else write it down
            with connection.cursor() as cursor:
                query = f"INSERT INTO registrants ({fields}) VALUES ({s})"
                cursor.execute(query, list(registrant.values()))
            connection.commit()


def clear_reports():
    for report_filename in os.listdir(REPORTS_DIR):
        try:
            os.remove(os.path.join(REPORTS_DIR, report_filename))
        except:
            pass


def configure_logging(file_name):
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), file_name)

    # set up
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(file_path)

    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.INFO)

    c_format = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s', datefmt='%H:%M:%S')
    f_format = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')

    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    # clean the log
    log_size = os.path.getsize(file_path)

    if log_size > 500000:
        command = r'>' + file_path
        os.system(command)

    return logger


if __name__ == "__main__":
    # testing
    from config import DATABASE

    regs = get_registrants_from_csv()
    write_registrants_to_db(
        registrants=regs,
        db_host=DATABASE["host"],
        db_name=DATABASE["name"],
        db_login=DATABASE["user"],
        db_pass=DATABASE["password"],
    )
