#!/usr/bin/env python3

# This example will return the ERRORs from the last hour
import argparse
import logging
import pkg_resources
import subprocess
import sys
import traceback
from importlib import reload


def install(*modules):
    """
    Install the required Python modules if they are not installed.
    See https://stackoverflow.com/a/44210735
    Search for modules: https://pypi.org/
    :param modules: list of required modules
    :return: None
    """
    if not modules:
        return
    required = set(modules)
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = required - installed

    if missing:
        logging.info(f'Installing modules:', *missing)
        try:
            python = sys.executable
            subprocess.check_call([python, '-m', 'pip', 'install', '--upgrade', *missing], stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as err:
            logging.error(f'Failed to install the required modules: {missing}')
            logging.error(err)
            exit(1)


requirements = {'datetime', 'glob2', 'synology_abfb_log_parser'}
try:
    import datetime
    import glob
    import synology_abfb_log_parser
except ModuleNotFoundError:
    # FIXME: datetime should be in the base distro
    # FIXME: Is glob2 necessary? Will glob work?
    if sys.platform == 'win32':
        install(*requirements)
    else:
        logging.error(f'Required modules are not installed: {requirements}')
        logging.error('Automatic module installation is supported only on Windows')
        exit(1)

# Only update the Synology log parser
requirements = {'synology_abfb_log_parser'}
if sys.platform == 'win32':
    install(*requirements)

# Reload the modules if they were installed or updated.
reload(datetime)
reload(glob)
reload(synology_abfb_log_parser)


def main(logger=logging.getLogger(), ago_unit='days', ago_value=1, log_path='', log_glob='log.txt*'):
    # timedelta docs: https://docs.python.org/3/library/datetime.html#timedelta-objects
    # Note: 'years' is not valid. Use 'days=365' to represent one year.
    # Values include:
    #   weeks
    #   days
    #   hours
    #   minutes
    #   seconds
    after = datetime.timedelta(**{ago_unit: ago_value})

    logger.debug('Instantiating the synology_activebackuplogs_snippet class')
    # Importing is done by package.subpackage.Class()
    synology = synology_abfb_log_parser.bfb_log_parser.ActiveBackupLogParser(
        # Search logs within the period specified.
        # timedelta() will be off by 1 minute because 1 minute is added to detect if the log entry is last year vs.
        # this year. This should be negligible.
        after=after,

        # Use different log location
        log_path=log_path,

        # Use different filename globbing
        filename_glob=log_glob,

        # Pass the logger
        logger=logger
    )

    # Load the log entries
    logger.debug(f'Loading log files in "{log_path}"')
    synology.load()

    # Search for entries that match the criteria.
    find = {
        'priority': 'ERROR',
    }
    logger.debug('Searching the log files')
    found = synology.search(find=find)
    ts = (datetime.datetime.now() - after).strftime('%Y-%m-%d %X')
    if not found:
        logger.info(f"No log entries found since {ts}")
        return

    # True if log entries were found
    errors_found = False

    # Print the log events
    logger.debug('Printing the results')
    print(f'Log entries were found since {ts}:')
    for event in found:

        try:
            # Need to check if the keys are in the event. An error is thrown if a key is accessed that does not exist.
            if 'json' not in event or event['json'] is None:
                continue
            if 'backup_result' not in event['json']:
                continue
            if 'last_success_time' not in event['json']['backup_result']:
                continue
            if 'last_backup_status' not in event['json']['backup_result']:
                continue

            # Nicely formatted timestamp
            ts = event['datetime'].strftime('%Y-%m-%d %X')
            ts_backup = datetime.datetime.fromtimestamp(event['json']['backup_result']['last_success_time'])
            delta_backup = datetime.datetime.now() - ts_backup
            # delta_backup.days is an integer and does not take into account hours.
            if event['json']['backup_result']['last_backup_status'] == 'complete' and delta_backup.days >= 3:
                errors_found = True

            # Always print the output, so it's visible to the users.
            task_name = ''
            transferred = 0
            if 'running_task_result' in event['json']:
                if 'task_name' in event['json']['running_task_result']:
                    task_name = event['json']['running_task_result']['task_name']
                if 'transfered_bytes' in event['json']['running_task_result']:
                    transferred = event['json']['running_task_result']['transfered_bytes']

            print(f"{ts}: {event['json']['backup_result']}    Task name: '{task_name}'    Transferred: '{transferred}'    Days/Hours ago: {delta_backup}")
        except TypeError as err:
            logging.warning(f'Failed to check for key before using. Skipping this event. ERR: {err}')
            logging.warning(traceback.format_exc())
            logging.warning(f'Event: {event}')
            continue

    if errors_found:
        # Errors found. Exit with failure
        exit(1)
    else:
        # No errors found. Exit successful
        exit(0)


# Main entrance here...
if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Parse the Synology Active Backup for Business logs.')
    parser.add_argument('--log-level', default='info', dest='log_level',
                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help='set log level for the Synology Active Backup for Business module')
    parser.add_argument('--log-path', default='', type=str,
                        help='path to the Synology log files')
    parser.add_argument('--log-glob', default='log.txt*', type=str,
                        help='filename glob for the log files')
    parser.add_argument('--ago-unit', default='days', type=str,
                        help='time span unit, one of [seconds, minutes, hours, days, weeks]')
    parser.add_argument('--ago-value', default='1', type=int,
                        help='time span value')
    args = parser.parse_args()

    # Change default log level to INFO
    default_log_level = 'INFO'
    if args.log_level:
        default_log_level = args.log_level.upper()
    log_format = '%(asctime)s %(funcName)s(%(lineno)d): %(message)s'
    logging.basicConfig(format=log_format, level=default_log_level)
    top_logger = logging.getLogger()
    top_logger.setLevel(default_log_level)

    main(**{
        'logger': top_logger,
        'log_path': args.log_path,
        'log_glob': args.log_glob,
        'ago_unit': args.ago_unit,
        'ago_value': args.ago_value
    })
