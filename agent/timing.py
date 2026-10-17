from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from time import perf_counter


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


@contextmanager
def timer(name: str):
    started = perf_counter()
    status = "SUCCESS"

    print(
        f"\n[TIME START] {timestamp()} | {name}",
        flush=True,
    )

    try:
        yield
    except BaseException:
        status = "FAILED / INTERRUPTED"
        raise
    finally:
        elapsed = perf_counter() - started

        print(
            f"\n[TIME END] {timestamp()} | {name}"
            f" | {status} | {elapsed:.2f} seconds",
            flush=True,
        )


def timed(name: str):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            with timer(name):
                return function(*args, **kwargs)

        return wrapper

    return decorator