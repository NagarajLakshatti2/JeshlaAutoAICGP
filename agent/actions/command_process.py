"""Bounded command execution with receipt-backed cooperative stop requests."""
import os
import subprocess
import time


def run_command(tools, command, timeout, cancelled):
    argv = tools._command_argv(command, timeout)
    process = subprocess.Popen(argv, cwd=tools.root, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", errors="replace", shell=False)
    deadline = time.monotonic() + timeout
    stopped = False
    timed_out = False
    try:
        while True:
            stopped = cancelled()
            timed_out = time.monotonic() >= deadline
            if stopped or timed_out:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                if process.poll() is None:
                    process.kill()
                stdout, stderr = process.communicate(timeout=10)
                break
            try:
                stdout, stderr = process.communicate(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                continue
        return {"command": command, "exit_code": process.returncode,
                "stdout": stdout[-12000:], "stderr": stderr[-12000:],
                "output_truncated": len(stdout) > 12000 or len(stderr) > 12000,
                "timed_out": timed_out, "cancelled": stopped}
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        for stream in (process.stdout, process.stderr):
            stream.close()
