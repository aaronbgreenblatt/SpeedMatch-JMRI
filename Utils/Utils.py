import traceback
from functools import wraps

"""
This function prints a copy of exceptions and their
traceback to stdout before rethrowing the exception.
The function is useful because JMRI sends stderr to
the messages log file rather than to the "Script
Output" window in the JMRI program.

Use this as a decorator
"""
def RedirectStdErr(wrapped_func):
    @wraps(wrapped_func)
    def RedirectStdErrWrapper(*args, **kwargs):
        try:
            r = wrapped_func(*args, **kwargs)
        except Exception as err:
            print('Jython Exception: ', err)
            print('Jython Stack Trace: ', traceback.format_exc())
            print('Further details in JMRI log/messages file, typically ~/JMRI/log/messages')
            raise
        return r

    return RedirectStdErrWrapper

def median(lst):
    n = len(lst)
    s = sorted(lst)
    return (s[n//2-1]/2.0+s[n//2]/2.0, s[n//2])[n % 2] if n else None
