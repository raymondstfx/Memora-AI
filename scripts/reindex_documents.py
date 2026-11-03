"""Explicitly enqueue index rebuilds after changing backend embedding profile."""

import argparse
import json
from urllib.request import Request, urlopen
from uuid import UUID


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--all", action="store_true")
    target.add_argument("--document", type=UUID)
    parser.add_argument("--reparse", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/") + "/api"
    if args.all:
        with urlopen(base + "/documents", timeout=15) as response:
            identifiers = [row["id"] for row in json.loads(response.read())]
    else:
        identifiers = [str(args.document)]
    for identifier in identifiers:
        request = Request(
            base + f"/documents/{identifier}/reindex",
            data=json.dumps({"reparse": args.reparse}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=15) as response:
            print(json.loads(response.read()))
    print(
        "Rebuilds queued. Poll Knowledge Base/job status; queued does not mean ready."
    )


if __name__ == "__main__":
    main()
