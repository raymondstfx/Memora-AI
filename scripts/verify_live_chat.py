"""Explicit opt-in live chat smoke test; never reads or prints the API key."""

import argparse
import json
from urllib.request import Request, urlopen
from uuid import uuid4


def get(base: str, path: str):
    with urlopen(base.rstrip("/") + "/api" + path, timeout=20) as response:
        return json.loads(response.read())


def send(base: str, message: str, conversation_id: str | None = None):
    body = json.dumps(
        {
            "message": message,
            "conversation_id": conversation_id,
            "request_id": str(uuid4()),
        }
    ).encode()
    request = Request(
        base.rstrip("/") + "/api/chat/stream",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    frames = []
    with urlopen(request, timeout=330) as response:
        for raw in response:
            if raw.startswith(b"data: "):
                event = json.loads(raw[6:])
                frames.append(event)
                if event["event"] == "token":
                    print(event["text"], end="", flush=True)
    print()
    assert frames and frames[-1]["event"] == "message_end", frames[-1:]
    cid = frames[0]["conversation_id"]
    content = "".join(event.get("text", "") for event in frames)
    history = get(base, f"/conversations/{cid}/messages")
    assert history[-1]["status"] == "complete"
    assert history[-1]["content"] == content
    return cid, content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--run-live",
        action="store_true",
        help="Allow real, potentially billed model requests",
    )
    parser.add_argument(
        "--conversation",
        help="Only verify saved history after a restart; no model call",
    )
    args = parser.parse_args()
    if args.conversation:
        rows = get(args.base_url, f"/conversations/{args.conversation}/messages")
        assert rows and rows[-1]["status"] == "complete"
        print(f"PASS: {len(rows)} persisted messages after restart")
        return
    if not args.run_live:
        parser.error(
            "Add --run-live to enable real model requests, "
            "or --conversation to inspect saved history only."
        )
    config = get(args.base_url, "/chat/config")
    if not config["configured"]:
        raise SystemExit(config["message"])
    marker = f"memora-{uuid4().hex[:12]}"
    cid, _ = send(
        args.base_url,
        f"Remember this verification marker: {marker}. Acknowledge briefly.",
    )
    _, answer = send(
        args.base_url,
        "What was the verification marker? Reply only with the marker.",
        cid,
    )
    assert marker in answer, (
        "Model did not recall marker; investigate provider/context behavior"
    )
    other, _ = send(args.base_url, "Say hello briefly in Chinese.")
    assert other != cid
    print(
        "PASS: live SSE, history, context recall and separate conversations. "
        f"Conversation: {cid}"
    )
    print(
        "After restarting API/Postgres: "
        f"python scripts/verify_live_chat.py --conversation {cid}"
    )


if __name__ == "__main__":
    main()
