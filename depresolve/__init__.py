
import logging, time # both for the general logging setup across modules

class NoSatisfyingVersionError(Exception):
  pass

class ConflictingVersionError(Exception):
  pass

class UnresolvableConflictError(Exception):
  pass

class MissingDependencyInfoError(Exception):
  pass


# Logging configuration

## General logging configuration:
_FORMAT_STRING = '[%(asctime)sUTC] [%(name)s] %(levelname)s '+\
    '[%(filename)s:%(funcName)s():%(lineno)s]\n%(message)s\n'
_TIME_STRING = "%Y.%m.%d %H:%M:%S"

## File logging configuration:
LOG_FILENAME = 'depresolve.log'
file_handler = logging.FileHandler(LOG_FILENAME)
file_handler.setLevel(logging.DEBUG)
logging.Formatter.converter = time.gmtime
file_handler.setFormatter(logging.Formatter(_FORMAT_STRING, _TIME_STRING))

## Console logging configuration:
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(_FORMAT_STRING, _TIME_STRING))

## Logger instantiation
logger = logging.getLogger('depresolve')
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)
