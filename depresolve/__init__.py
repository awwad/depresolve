
import logging
logging.basicConfig(level=logging.DEBUG) # filename='resolver.log'

class NoSatisfyingVersionError(Exception):
  pass

class ConflictingVersionError(Exception):
  pass

class UnresolvableConflictError(Exception):
  pass

