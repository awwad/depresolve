"""

This code is drawn from:
http://www.saltycrane.com/blog/2010/04/using-python-timeout-decorator-uploading-s3/

I have corrected two minor python 3 incompatibilities in it. (Sebastien Awwad)

It provides a decorator that allows one to cause arbitrary functions to
timeout.

It is not threadsafe and requires the signals library, which is available only
on *NIX-like systems.

Throws "TimeoutException" (note: not TimeoutError, which is python 3 native)
when a function times out.
"""


import signal

class TimeoutException(Exception):
    def __init__(self, value = "Timed Out"):
        self.value = value
    def __str__(self):
        return repr(self.value)

def timeout(seconds_before_timeout):
    def decorate(f):
        def handler(signum, frame):
            raise TimeoutError()
        def new_f(*args, **kwargs):
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds_before_timeout)
            try:
                result = f(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old)
            signal.alarm(0)
            return result
        new_f.__name__ = f.__name__
        return new_f
    return decorate
