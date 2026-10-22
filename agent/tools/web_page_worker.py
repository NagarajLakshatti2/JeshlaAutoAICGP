"""Private worker for the bounded public page reader; never launches model code."""
import json
import sys
from agent.tools.web_pages import _fetch_in_process


def main():
    try:
        request=json.loads(sys.stdin.read(4096))
        result=_fetch_in_process(request["url"])
    except Exception:
        result={"error":"Public page reader failed; no page evidence retrieved."}
    sys.stdout.write(json.dumps(result,ensure_ascii=True))

if __name__=="__main__":
    main()
