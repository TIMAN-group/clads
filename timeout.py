"""
@see https://pythonadventures.wordpress.com/2012/12/08/raise-a-timeout-exception-after-x-seconds/
"""

import signal
import time
 
class Timeout():
    """Timeout class using ALARM signal."""
    class Timeout(Exception):
        pass
 
    def __init__(self, sec):
        self.sec = sec
 
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.sec)
 
    def __exit__(self, *args):
        signal.alarm(0)
 
    def raise_timeout(self, *args):
        raise Timeout.Timeout()
