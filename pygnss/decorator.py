import gzip
from functools import wraps
import subprocess
import warnings


def deprecated(alternative):
    def decorator(func):
        def new_func(*args, **kwargs):
            # Raise a DeprecationWarning with the specified message.
            message = f"Call to deprecated function {func.__name__}."
            if alternative:
                message += f" Use {alternative} instead."
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return new_func
    return decorator


def read_contents(func):
    """
    Decorator to handle gzip compression based on filename and pass its contents
    to the function
    """

    @wraps(func)
    def wrapper(filename, *args, **kwargs):

        doc = None

        if filename.endswith('.gz'):
            with gzip.open(filename, 'rt', encoding='utf-8') as fh:
                doc = fh.read()
        elif filename.endswith('.Z'):
            result = subprocess.run(['uncompress', '-c', filename],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    check=True,
                                    text=True)
            doc = result.stdout
        else:
            with open(filename, 'rt', encoding='utf-8') as fh:
                doc = fh.read()

        return func(doc, *args, **kwargs)

    return wrapper
