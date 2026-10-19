# Execution and offline-test logs

Automatic logging added 18 October 2026. Applies to newly started processes, not an already running test command.

## Offline test progress

Run `python tests/run_offline.py`. It prints the exact path of a new outputs/logs/offline-tests-TIMESTAMP-PID.jsonl file. Records are flushed as tests execute: run/discovery start/end, test start/end, duration and result, final counts or interruption. A final run_finished passed record is required for acceptance. A test_started record without its test_finished means that test was active when the process stopped or the log was last read; it does not itself prove deadlock. No assertion messages, private fixture text or raw tracebacks are saved in this progress log; terminal diagnostics remain available separately. If the log file cannot be created, tests still run with a warning.

## Console and browser runtime

Shared timing stages append to outputs/logs/execution-PID.jsonl. Separate PID files avoid console/browser rotation collisions. Each file rotates after about 2 MB with two retained rotations; old process files are retained until deliberately cleaned up. Start/end records share a span ID and include stage, duration and outcome. Provider failures can include a whitelisted provider/category and HTTP status. Prompts, answers, keys, file contents and raw error text are excluded. Logging failure does not break the application. Only instrumented stages are covered; this is not a complete execution trace or token-usage audit.

Existing browser metadata remains in outputs/logs/browser-activity.jsonl. These logs are local diagnostics; do not commit or publish them automatically.

## Reading a current log

Open a second terminal in the project and read the path printed by the test runner, for example `Get-Content outputs/logs/offline-tests-...jsonl -Tail 10 -Wait`. Keep tests serial when diagnosing performance. Do not rerun the entire suite concurrently merely to get logs. Restart console/Streamlit to load new runtime logging.

## User-run evidence

The supplied run completed 360 tests in 990.841 seconds with six errors. Shown errors are subprocess and AppTest timeouts, not assertion mismatches. This is a failed run; no acceptance is claimed and timeout thresholds have not been increased. Logs should guide diagnosis before attributing the cause to hardware or refactoring.
