
import logging
logging.basicConfig(level=logging.INFO) # filename='resolver.log'

class NoSatisfyingVersionError(Exception):
  pass

class ConflictingVersionError(Exception):
  pass

class UnresolvableConflictError(Exception):
  pass

