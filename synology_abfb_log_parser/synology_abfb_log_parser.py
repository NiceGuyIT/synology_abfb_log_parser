# Synology Active Backup for Business log parser
# Version: 0.1.0
# Author: David Randall
# GitHub: https://github.com/NiceGuyIT/synology_abfb_log_parser
# PyPi: https://pypi.org/project/synology-abfb-log-parser/
# URL: https://NiceGuyIT.biz
#
import datetime
import glob
import json
import logging
import os.path
import re
import sys
import traceback


def fix_single_quotes(json_str):
    """
    fix_single_quotes will replace JSON-type strings containing double quotes with single quotes to make the entire
    string valid JSON.

    Example:
    Given the string
        "task_template": {"backup_cache_content": "{"cached_enabled":false}"}
    the double quotes inside "{...}" will be replaced with single quotes resulting in
        "task_template": {"backup_cache_content": "{'cached_enabled':false}"}

    :param json_str: json_str
    :return cleaned: string
    """
    if not json_str:
        return json_str

    re_left = re.compile(r'"\{')
    re_right = re.compile(r'}"')
    left = re.split(re_left, json_str)
    if not left:
        return json_str

    cleaned = ''
    for index, val in enumerate(left):
        if index == 0:
            # The first value is valid JSON.
            cleaned = val
            continue

        # The right should split into only 2 pieces
        right = re.split(re_right, val)
        if len(right) != 2:
            logging.error('Could not fix JSON with single quotes')
            logging.error(f'JSON string: {json_str}')
            logging.error(f'left: {left}')
            logging.error(f'right: {right}')
            return json_str

        # The first piece is invalid and needs double quotes replaced with single quotes.
        # The second piece is valid JSON
        cleaned += '"{' + right[0].replace('"', "'") + '}"' + right[1]

    return cleaned


def fix_simple(json_str):
    """
    fix_simple will perform simple replacements to fix invalid JSON strings.

    Example:
    Given the string
        "snapshot_info": {"data_length": 18739, }, "subaction": "update_device_spec"
    the ", }" will be replaced with "}" resulting in
        "snapshot_info": {"data_length": 18739}, "subaction": "update_device_spec"

    Given the string
        "volume_name": "\\?\Volume{12345678-1234-abcd-1234-12345678abcd}\"},
    the backslashes are escaped with a backslash resulting in
        "volume_name": "\\\\?\\Volume{12345678-1234-abcd-1234-12345678abcd}\\"},

    :param json_str: json_str
    :return cleaned: string
    """
    if not json_str:
        return json_str
    return json_str.replace(', }', '}').replace('\\', '\\\\')


class SynologyActiveBackupLogParser(object):
    """
    SynologyActiveBackupLogParser will consume Synology Active Backup logs, parse them and make them available for
    searching.
    """

    def __init__(self, after=datetime.timedelta(days=1), log_path=None, filename_glob=None,
                 logger=None):
        """
        Initialize class parameters.

        :param after: datetime.timedelta of how far back to search.
        :param log_path: string path to the log files
        :param filename_glob: string filename glob pattern for the log files
        :param logger: logging instance
        """

        # Logging framework
        if logger is None:
            # If a logger isn't passed, set log level to error.
            self.__logger = logging.getLogger()
            self.__logger.setLevel(logging.ERROR)
        else:
            self.__logger = logger

        # Filename glob for logs
        self.__log_filename_glob = 'log.txt*'
        if filename_glob:
            self.__log_filename_glob = filename_glob

        # Path to log files
        self.__log_path = None
        if sys.platform == 'linux' or sys.platform == 'linux2':
            self.__log_path = '/var/log/activebackupforbusinessagent'
        elif sys.platform == 'darwin':
            self.__log_path = '/var/log/activebackupforbusinessagent'
        elif sys.platform == 'win32':
            self.__log_path = 'C:\\ProgramData\\ActiveBackupForBusinessAgent\\log'
        # Log path was provided
        if log_path:
            self.__log_path = log_path

        # __re_timestamp is a regular expression to extract the timestamp from the beginning of the logs.
        self.__re_log_entry = re.compile(r'^(?P<month>\w{3}) (?P<day>\d+) (?P<time>[\d:]{8}) \[(?P<priority>\w+)] (?P<method_name>[\w.-]+) \((?P<method_num>\d+)\): ?(?P<message>.*)$')

        # __now is a timestamp used to determine if the log entry is after "now". 1 minute is added for
        # processing time.
        self.__now = datetime.datetime.now() + datetime.timedelta(minutes=1)

        # __current_year is the current year and used to determine if the log entry is for this year or last year.
        # The logs do not contain the year.
        self.__current_year = self.__now.year

        # __after is a timestamp used to calculate if the log should be included in the search.
        # Default: 1 day
        if after:
            self.__after = after

        # __events is an array of the log entries.
        self.__events = []

    def load(self):
        """
        Load will load all the log files in the path that have a timestamp after the time delta to search for.

        :return: None
        """
        if not os.path.isdir(self.__log_path):
            self.__logger.error(f'Error: Log directory does not exist: {self.__log_path}')
            return None

        files = glob.glob(os.path.join(self.__log_path, self.__log_filename_glob))
        files.sort(key=os.path.getmtime)
        for file in files:
            if datetime.datetime.fromtimestamp(os.path.getmtime(file)) > datetime.datetime.now() - self.__after:
                self.__logger.debug(f'Processing log file: {file}')
                self.load_log_file(file)

        return None

    def load_log_file(self, log_path):
        """
        load_log_file will iterate over the log files and load the log entries into an object.

        :param log_path: string path to the log files
        :return: None
        """
        # Use the correct encoding.
        # https://stackoverflow.com/questions/17912307/u-ufeff-in-python-string/17912811#17912811
        #   Note that EF BB BF is a UTF-8-encoded BOM. It is not required for UTF-8, but serves only as a
        #   signature (usually on Windows).
        with open(log_path, mode='r', encoding='utf-8-sig') as fh:
            for line in fh.readlines():
                ts_match = self.__re_log_entry.match(line)
                if ts_match:
                    # New log entry
                    # Check if the timestamp is before the threshold
                    # TODO: Use f-strings
                    # ts = datetime.datetime.strptime('{year} {month} {day} {time}'.format(
                    #     month=ts_match.group('month'),
                    #     day=ts_match.group('day'),
                    #     time=ts_match.group('time'),
                    #     year=self.__current_year,
                    # ), '%Y %b %d %X')
                    ts = datetime.datetime.strptime(
                        f'{self.__current_year} {ts_match.group("month")} {ts_match.group("day")} {ts_match.group("time")}',
                        '%Y %b %d %X')
                    if self.__now < ts:
                        # Log timestamp is in the future indicating the log entry is from last year. Subtract one year.
                        # FIXME: This does not take into account leap years. It may be off 1 day on leap years.
                        ts = ts - datetime.timedelta(days=365)

                    if self.__now - self.__after < ts:
                        # Log timestamp is after the 'after' timestamp. Include it.
                        # Always include the timestamp
                        self.__events.append({
                            'datetime': ts,
                            'timestamp': f'{ts_match["month"]} {ts_match["day"]} {ts_match["time"]}',
                            'priority': ts_match['priority'],
                            'method_name': ts_match['method_name'],
                            'method_num': ts_match['method_num'],
                            'message': ts_match['message'].strip(),
                            # 'json_str': None,
                            'json': None,
                        })

                else:
                    # Multiline log entry; append to last line
                    if len(self.__events) == 0:
                        # Log timestamp was before the 'after' window and nothing is captured yet.
                        continue
                    self.__events[len(self.__events) - 1]['message'] += line.strip()

    def parse_json(self, index):
        """
        parse_json will extract the JSON strings from the message and store them in "json".

        :param index: int index of entry to parse
        :return: None
        """
        # Ignore strings that look like JSON but aren't. This is to prevent false JSON parsing errors.
        re_ignore_list = [
            re.compile(r'getVolumeDetailInfo for .*Volume'),
            re.compile(r'Snapshot: \{'),
            re.compile(r'Create snapshot for'),
        ]
        for regex in re_ignore_list:
            matches = re.search(regex, self.__events[index]['message'])
            if matches:
                # Fake JSON found. Don't continue the search.
                self.__logger.debug(f'Ignoring fake JSON: {self.__events[index]["message"]}')
                return

        # If the message has what looks like JSON, extract it from the payload.
        re_list = [
            re.compile(r"'(?P<json>{.*})'"),
            re.compile(r'([^{]*)(?P<json>\{".*})(.*)'),
        ]
        for regex in re_list:
            matches = re.search(regex, self.__events[index]['message'])
            if matches:

                # Fix single quotes
                # Fix commas without values
                json_str = fix_simple(fix_single_quotes(matches['json']))
                try:
                    self.__events[index]['json'] = json.loads(json_str, strict=False)
                    # self.__logger.debug('JSON Object:', self.__events[index]['json'])
                    # Valid JSON found. Don't need to look for more.
                    return
                except json.decoder.JSONDecodeError as err:
                    self.__logger.error('ERR: Failed to parse JSON from message')
                    self.__logger.error('Input JSON string:')
                    self.__logger.error(json_str)
                    self.__logger.error('Input log string:')
                    self.__logger.error(self.__events[index]['message'])
                    self.__logger.error(self.__events[index])
                    self.__logger.error(err)
                    self.__logger.error(traceback.format_exc())
                    self.__logger.error('-----')

    def search(self, find):
        """
        search will iterate over the log entries searching for lines that match the values in find.
        find is required.

        :param find: dict representing the log entries to find.
        :return: dict of the log entries.
        """
        for x in range(len(self.__events)):
            self.parse_json(index=x)
            if not self.is_subset(find, self.__events[x]):
                # Event doesn't match search. Mark it for removal.
                self.__events[x] = None
        # Remove events marked for removal.
        self.__events = [x for x in self.__events if x is not None]
        return self.__events

    def is_subset(self, subset, superset):
        """
        is_subset will recursively compare two dictionaries and return true if subset is a subset of the superset.
        See https://stackoverflow.com/a/57675231

        :param subset: dict of the subset
        :param superset: dict of the superset
        :return: true if subset is a subset of the superset
        """
        if subset is None or superset is None:
            return False

        if isinstance(subset, dict):
            return all(key in superset and self.is_subset(val, superset[key]) for key, val in subset.items())

        if isinstance(subset, list) or isinstance(subset, set):
            return all(any(self.is_subset(subitem, superitem) for superitem in superset) for subitem in subset)

        # assume that subset is a plain value if none of the above match
        return subset == superset
