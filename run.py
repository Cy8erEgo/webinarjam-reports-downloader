import argparse

from models import WebinarjamController
from utils import (
    get_registrants_from_csv,
    write_registrants_to_db,
    clear_reports,
    configure_logging,
)
from config import *


HEADLESS = True

# set up argparse
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
    "-e",
    "--event",
    default="yesterday",
    choices=[
        "yesterday",
        "all time",
        "today",
        "this week",
        "last week",
        "last 7 days",
        "this month",
        "last month",
        "last 30 days",
    ],
)
args = arg_parser.parse_args()

# set up logging
logger = configure_logging("debug.log")


def main():
    try:
        logger.info("start")

        # delete old reports
        clear_reports()

        # try to download all reports from the site
        # 3 attempts
        for _ in range(3):
            try:
                logger.info("step 1: scraping reports")

                app = WebinarjamController(
                    SITE_LOGIN, SITE_PASSWD, headless=HEADLESS, logger=logger
                )
                app.get_all_reports(event=args.event)  # for all webinars
                break
            except Exception:
                logger.error("failed to download reports", exc_info=True)
        else:
            logger.error("3 failed attempts achieved, terminating the program")

        # get all registrants from the downloaded csv reports (in the reports directory)
        logger.info("step 2: getting all registrants from all reports")
        registrants = get_registrants_from_csv()
        logger.info("step 2: got {} registrant(s)".format(len(registrants)))

        # write the registrants to the database
        logger.info("step 3: writing the registrants to the database")
        write_registrants_to_db(
            registrants=registrants,
            db_host=DATABASE["host"],
            db_name=DATABASE["name"],
            db_login=DATABASE["user"],
            db_pass=DATABASE["password"],
        )

        logger.info("profit!")
    except KeyboardInterrupt:
        logger.info("exited")
    except Exception:
        logger.critical("critical error occurred", exc_info=True)


if __name__ == "__main__":
    main()
