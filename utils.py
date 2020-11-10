from threading import Lock
from contextlib import contextmanager


def swallow_exceptions(exception_logger=None):
    '''
    Decorator
    '''
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                if exception_logger is not None:
                    exception_logger.error(e)

        return wrapper

    return decorator


def log_call(logger, msg: str):
    '''
    Decorator that logs each function call
    '''
    def deco(f):
        def wrapper(*args, **kwargs):
            logger.info(msg)
            return f(*args, **kwargs)

        return wrapper

    return deco


class CsvWriter:
    def __init__(self, filename, header=None, encoding='cp932'):
        '''
        CSV file writer.
        Output file gets created on the first 'add_line' call and thus no empty file.
        Args:
            filename: filename
            header (str): (Optional) header
        '''
        self.filename = filename
        self.header = header
        self.encoding = encoding
        self.initialized = False

    def add_line(self, line):
        if not self.initialized:
            with open(self.filename, 'w', encoding=self.encoding) as file:
                if self.header is not None and self.header != '':
                    file.write(self.header)
                    if self.header[-1] != '\n':
                        file.write('\n')

            self.initialized = True

        with open(self.filename, 'a', encoding=self.encoding) as file:
            file.write(line)
            if line != '' and line[-1] != '\n':
                file.write('\n')


class Locker:
    def __init__(self):
        self.lock_obj = Lock()

    @contextmanager
    def lock(self):
        self.lock_obj.acquire()
        try:
            yield
        finally:
            self.lock_obj.release()
