from models import WebinarjamController
from config import *


app = WebinarjamController(SITE_LOGIN, SITE_PASSWD)
app.get_all_reports()  # for all webinars
