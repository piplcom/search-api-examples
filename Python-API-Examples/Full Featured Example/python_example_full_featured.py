#!python3
# Threading from http://stackoverflow.com/questions/16199793/python-3-3-simple-threading-event-example
import threading
from queue import Queue

from datetime import datetime
import time
from timeit import default_timer as timer
import csv
import logging
from limit import limit
from pathlib import Path
import phonenumbers

from piplapis.search import SearchAPIRequest, Source, SearchAPIResponse
from piplapis.error import APIError
from piplapis.data import Person, Address, Name, Phone, Email, Job, DOB
from piplapis.data.fields import DateRange, URL, Username, UserID

# --------Configure input and output file paths + logging ------

INPUT_FILE_PATH = Path('Pipl_test_input_data.csv')
OUTPUT_FOLDER_PATH = Path('json_output_test/')
LOG_FOLDER_PATH = Path('Pipl_logs/')

# ---------------------------------------------------------------

# -------Script Configuration -------------------------


MAX_QPS = 20 # If Live_feeds are on, change MAX_QPS to 10
NUMBER_OF_THREADS = 10
THROTTLE_SLEEP_TIME = NUMBER_OF_THREADS/MAX_QPS
MAX_RETRY = 5  # number of times to retry a request if get a 403 throttle reached
LOG_LEVEL = logging.WARNING

# -------Set API key and configuration parameters -----------------
PIPL_KEY = 'YOUR KEY' # Replace with your BUSINESS PREMIUM key - see https://pipl.com/api/manage/keys
SearchAPIRequest.set_default_settings(api_key=PIPL_KEY, top_match=True,
                                      minimum_probability=0.6, live_feeds=False)
# --------------------------------------------------------

# -------------- CSV Column headers and indexes ---------------------

IS_FIRST_HEADER = True

#Modify the header list to match your input CSV data
IDX_UNIQUE_ID = 0
IDX_LINKEDIN_URL = 1
#IDX_USERNAME
#IDX_USER_ID
IDX_NAME_FIRST = 2
IDX_NAME_LAST = 3
IDX_ADDRESS = 4
    #IDX_ADDRESS_COUNTRY
    #IDX_ADDRESS_STATE
    #IDX_ADDRESS_CITY
    #IDX_ADDRESS_STREET
    #IDX_ADDRESS_HOUSE
    #IDX_ADDRESS_ZIP
IDX_COMPANY_NAME = 5
#IDX_JOB_TITLE
IDX_EMAIL = 6
IDX_PHONE = 7

class ResultStatistics:
    perfect_matches = 0
    possible_matches = 0
    no_matches = 0
    error_rows = 0
    email_fill = 0
    phone_fill = 0
    # social_fill = 0


results = ResultStatistics
# ----------------------------------------------------------

# ------------ init logging ------------------------------#
# logging to indicate info, warnings and errors
logger = logging.getLogger(__name__)

if not Path.exists(LOG_FOLDER_PATH):
    LOG_FOLDER_PATH.mkdir()
logFileName = datetime.now().strftime('%m-%d-%Y %H_%M_%S')
logFilePath = Path(str(LOG_FOLDER_PATH) + '/' + logFileName)
logFilePath.touch(exist_ok=True)

_handler = logging.FileHandler(logFilePath)
_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

logger.setLevel(LOG_LEVEL)
_handler.setLevel(LOG_LEVEL)
_handler.setFormatter(_formatter)

logger.addHandler(_handler)


# --------------------------------------------------------#
@limit(MAX_QPS, 1) # rate limiting for queries sent
def send_PIPL_query(request):
    return request.send()


def get_PIPL_response(request, row_no):
    retry_cnt = 0
    while True:
        retry_cnt = retry_cnt + 1
        if retry_cnt > MAX_RETRY:
            break

        try:
            start = timer()

            api_response = send_PIPL_query(request)
            end = timer()
            queryElapsedTime = end - start

            return api_response
        except ValueError as ve:
            with lock:
                logger.error(u"Row {} - {}".format(row_no, ve))
            break
        except APIError as api_error:
            with lock:

                # Check for QPS errors
                if api_error.http_status_code == 403:
                    is_over_throttle = False
                    if api_error.qps_current:
                        if (api_error.qps_current > api_error.qps_allotted):
                            is_over_throttle = True
                    if api_error.qps_live_current:
                        if (api_error.qps_live_current > api_error.qps_live_allotted):
                            is_over_throttle = True
                    if is_over_throttle is True:
                        logger.error(u"Row {} - Retry {}/{} - QPS LIVE:{}/{}. QPS TOTAL: {}/{}".format(row_no, retry_cnt, MAX_RETRY,
                                                                                                api_error.qps_live_current,
                                                                                                api_error.qps_live_allotted,
                                                                                                api_error.qps_current,
                                                                                                api_error.qps_allotted))
                        time.sleep(THROTTLE_SLEEP_TIME)
                        continue

                if api_error.http_status_code == 500:
                    logger.error(
                        u"Row {} - Retry {}/{} - Status Code:{} - {}".format(row_no, retry_cnt, MAX_RETRY, api_error.http_status_code, api_error.error))
                    continue

                if api_error.error:
                    logger.error(u"Row {} - Status Code:{} - {}".format(row_no, api_error.http_status_code, api_error.error))
                if api_error.warnings:
                    for warning in api_error.warnings:
                        logger.warning(u"Row {} - API Warning: {}".format(row_no, warning))

        except Exception as e:
            with lock:
                logger.exception(u"Row {} - {}".format(row_no, e))

        break
    return


def do_work(item):

    try:
        row_no = item[0]
        input_data = item[1]
        fields = []

        # extract next field from input data array

        # Name
        if input_data[IDX_NAME_FIRST] and input_data[IDX_NAME_LAST]:
            if (len(input_data[IDX_NAME_FIRST]) >= 2 or len(input_data[IDX_NAME_LAST]) >= 2):
                fields.append(
                    Name(
                        first=input_data[IDX_NAME_FIRST],
                        last=input_data[IDX_NAME_LAST]))

        # URL
        if input_data[IDX_LINKEDIN_URL]:
            fields.append(URL(url=input_data[IDX_LINKEDIN_URL]))

        # Username
        # if input_data[IDX_USERNAME]:
            # fields.append(Username(username=input_data[IDX_USERNAME]))

        # UserID
        # if input_data[IDX_USER_ID]:
            # fields.append(UserID(userID=input_data[IDX_USER_ID]))

        # Job
        if input_data[IDX_COMPANY_NAME]:
            fields.append(Job(organization=input_data[IDX_COMPANY_NAME]))

        # if input_data[IDX_JOB_TITLE]:
            # fields.append(Job(title=input_data[IDX_JOB_TITLE]))

        # Address 
        if input_data[IDX_ADDRESS]:
            fields.append(Address(raw=input_data[IDX_ADDRESS]))

        # Email
        if input_data[IDX_EMAIL]:
            if Email.re_email.match(input_data[IDX_EMAIL]):
                fields.append(Email(address=input_data[IDX_EMAIL]))
            else:
                logger.warning(
                    "Invalid email: Row {}, Row ID {},{}\n".format(row_no, input_data[IDX_UNIQUE_ID], input_data[IDX_EMAIL]))

        # Phone
        if input_data[IDX_PHONE]:
            try:
                if phonenumbers.is_possible_number(phonenumbers.parse(input_data[IDX_PHONE])):
                    fields.append(Phone(number=input_data[IDX_PHONE]))
                else:
                    logger.warning(
                        "Invalid phone: Row {}, Row ID {},{}\n".format(row_no, input_data[IDX_UNIQUE_ID], input_data[IDX_PHONE]))
            except AttributeError:
                logger.warning(
                    "Invalid phone: Row {}, Row ID {},{}\n".format(row_no, input_data[IDX_UNIQUE_ID],
                                                                   input_data[IDX_PHONE]))

        request = SearchAPIRequest(person=Person(fields=fields))
        api_response = get_PIPL_response(request, row_no)

        if api_response:
            if api_response.persons_count == 0:
                results.no_matches += 1

            if api_response.persons_count == 1:
                results.perfect_matches += 1
                if api_response.available_data.premium.emails:
                    results.email_fill += 1
                if api_response.available_data.premium.phones:
                    results.phone_fill += 1

            if api_response.persons_count > 1:
                results.possible_matches += 1

            file_name = u"{}_{}.json".format(row_no-1,
                                             input_data[IDX_UNIQUE_ID])
            json_file = Path.joinpath(OUTPUT_FOLDER_PATH, file_name)

            if api_response.warnings:
                for warning in api_response.warnings:
                    logger.warning(u"Row {} - API Warning: {}\n".format(row_no, warning))

            logger.info(u"Row {} results - {} saved".format(row_no, json_file))
            with lock:
                json_file = Path.joinpath(OUTPUT_FOLDER_PATH, file_name)
                with open(json_file, "w+", encoding='utf-8') as fp:
                    fp.write(api_response.raw_json)

        else:
            logger.warning(u"Row {} could not get API response".format(row_no))
            results.error_rows += 1

    except Exception as e:
        with lock:
            logger.exception(u"Row {}".format(row_no))

    with lock:
        logger.info(u"Row {} - {} {}".format(row_no, threading.current_thread().name, item))


def log_batch_info():
    logger.setLevel(logging.INFO)
    _handler.setLevel(logging.INFO)
    response_count = results.perfect_matches + results.possible_matches + results.no_matches
    logger.info("\n".join([u'\nTotal Pipl API Responses: {}'.format(response_count),
                          u'Perfect Matches: {0} - {1:.3g}%'.format(results.perfect_matches, 100 * results.perfect_matches / response_count),
                          u'Possible Matches: {0} - {1:.3g}%'.format(results.possible_matches,100 * results.possible_matches / response_count),
                          u'No Matches: {0} - {1:.3g}%'.format(results.no_matches, 100 * results.no_matches / response_count),
                          u'Could not read {} row(s)\n'.format(results.error_rows),
                          u'Of your Perfect matches, {0} responses({1:.3g}%) had an email in the response'.format(
                              results.email_fill, 100 * results.email_fill / results.perfect_matches),
                          u'Of your Perfect matches, {0} responses({1:.3g}%) had a phone in the response'.format(
                              results.phone_fill, 100 * results.phone_fill / results.perfect_matches)
                          ])
                )

# The worker thread pulls an item from the queue and processes it
def worker():
    while True:
        item = q.get()
        do_work(item)
        q.task_done()


if __name__ == '__main__':
    count = 0

    # lock to serialize console output
    lock = threading.Lock()

    # Create the queue and thread pool.
    q = Queue()
    for i in range(NUMBER_OF_THREADS):
        t = threading.Thread(target=worker)
        t.daemon = True  # thread dies when main thread (only non-daemon thread) exits.
        t.start()

    # Create Output folders if it doesn't exist
    if not Path.exists(OUTPUT_FOLDER_PATH):
        Path.mkdir(OUTPUT_FOLDER_PATH)

    # Put work items on the queue
    with open(INPUT_FILE_PATH) as csvfile_read:
        csvreader = csv.reader(csvfile_read, delimiter=',', quotechar='"')
        for row in csvreader:
            count += 1
            if (count == 1 and IS_FIRST_HEADER):
                continue
            item = [count, row]
            logger.info(u"Fetching record {} {}".format(count, item))

            q.put(item)

    q.join()  # block until all tasks are done

    log_batch_info()
    print('Your CSV file has finished processing')
