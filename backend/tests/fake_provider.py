"""Test-only HTTP upstream. Never imported or enabled by the production app."""

import asyncio
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pdf_fixtures import vector

app = FastAPI()
attempts: dict[str, int] = {}


@app.get("/health")
def health():
    return {"test_fixture": True}


@app.post("/v1/chat/completions")
async def complete(request: Request):
    body = await request.json()
    text = body["messages"][-1]["content"]
    try:
        payload = json.loads(text)
    except ValueError:
        payload = None
    if isinstance(payload, dict) and payload.get("evidence"):
        source = payload["evidence"][0]
        text = json.dumps(
            {
                "answer": source["text"] + " [" + source["key"] + "]",
                "source_refs": [source["key"]],
                "insufficient_evidence": False,
            }
        )
    attempts[text] = attempts.get(text, 0) + 1
    if "[fail-before]" in text or ("[fail-once]" in text and attempts[text] == 1):
        return JSONResponse({"error": "test failure"}, status_code=401)

    async def events():
        tokens = (
            [text]
            if isinstance(payload, dict) and payload.get("evidence")
            else ["Test fixture: ", "你好. ", text]
        )
        for token in tokens:
            await asyncio.sleep(0.15 if "[slow]" not in text else 2)
            yield (
                "data: "
                + json.dumps({"choices": [{"delta": {"content": token}}]})
                + "\n\n"
            )
            if "[fail-after]" in text:
                return
        yield (
            "data: "
            + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]})
            + "\n\n"
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    body = await request.json()
    return {
        "data": [
            {"index": i, "embedding": vector(text, body.get("dimensions", 16))}
            for i, text in enumerate(body["input"])
        ]
    }
