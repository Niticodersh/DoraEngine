"""FastAPI server exposing the decoupled DoraEngine backend."""
from __future__ import annotations

import asyncio
import json
import threading
from queue import Queue

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from api.constants import AGENT_STAGES, SUGGESTIONS
from api.service import generate_followup_questions, run_research_payload, stage_payload
from utils.pdf_export import generate_pdf


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


class FollowupRequest(BaseModel):
    query: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    count: int = Field(default=6, ge=1, le=10)


class PdfExportRequest(BaseModel):
    query: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    reasoning_steps: list[dict] = Field(default_factory=list)
    confidence: float = 0.0
    timestamp: str | None = None


app = FastAPI(title="DoraEngine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _http_error(exc: Exception) -> HTTPException:
    message = str(exc)
    status = 400 if isinstance(exc, ValueError) else 500
    return HTTPException(status_code=status, detail=message)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "message": "DoraEngine API is running"}


@app.get("/api/config")
def config() -> dict:
    return {"suggestions": SUGGESTIONS, "agent_stages": AGENT_STAGES}


@app.post("/api/research")
def research(request: ResearchRequest):
    try:
        return run_research_payload(request.query)
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/followups")
def followups(request: FollowupRequest) -> dict:
    try:
        return {
            "followups": generate_followup_questions(request.query, request.answer, request.count)
        }
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/export/pdf")
def export_pdf(request: PdfExportRequest):
    pdf_bytes = generate_pdf(
        query=request.query,
        answer=request.answer,
        sources=request.sources,
        reasoning_steps=request.reasoning_steps,
        confidence=request.confidence,
        timestamp=request.timestamp,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="doraengine-report.pdf"'},
    )


@app.post("/api/research/stream")
async def research_stream(request: ResearchRequest):
    queue: Queue = Queue()
    completion = threading.Event()

    def progress(agent: str, action: str) -> None:
        queue.put(
            {
                "type": "stage",
                "agent": agent,
                "action": action,
                "stage": stage_payload(agent),
            }
        )

    def worker() -> None:
        try:
            result = run_research_payload(request.query, progress_callback=progress)
            queue.put({"type": "complete", "result": result})
        except Exception as exc:
            queue.put({"type": "error", "error": str(exc)})
        finally:
            completion.set()

    threading.Thread(target=worker, daemon=True).start()

    async def event_stream():
        loop = asyncio.get_running_loop()
        while not (completion.is_set() and queue.empty()):
            item = await loop.run_in_executor(None, queue.get)
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
