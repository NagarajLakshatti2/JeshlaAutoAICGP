from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from time import perf_counter
from uuid import uuid4
from agent.runtime.execution_log import log_execution


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


class TimerOutcome:
    """Keep task outcomes separate from exception-free function returns."""
    def __init__(self):
        self.status="SUCCESS"

    def observe(self, result):
        if isinstance(result,dict):
            statuses={"completed":"SUCCESS","incomplete":"INCOMPLETE",
                      "failed":"FAILED","awaiting_input":"WAITING FOR INPUT"}
            self.status=statuses.get(result.get("task_status"),self.status)


@contextmanager
def timer(name: str):
    started = perf_counter()
    outcome = TimerOutcome()
    failure=None
    span=uuid4().hex
    log_execution("stage_started",name,span=span)

    print(
        f"\n[TIME START] {timestamp()} | {name}",
        flush=True,
    )

    try:
        yield outcome
    except BaseException as error:
        failure=error
        outcome.status = "FAILED / INTERRUPTED"
        raise
    finally:
        elapsed = perf_counter() - started
        log_execution("stage_finished",name,span=span,status=outcome.status,duration=elapsed,error=failure)

        print(
            f"\n[TIME END] {timestamp()} | {name}"
            f" | {outcome.status} | {elapsed:.2f} seconds",
            flush=True,
        )


def timed(name: str):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            with timer(name) as outcome:
                result=function(*args, **kwargs)
                outcome.observe(result)
                return result

        return wrapper

    return decorator