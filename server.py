import hashlib, hmac, os
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

EMAIL = "25ds3000071@ds.study.iitm.ac.in".strip().lower()
app = FastAPI()

TOOL = {
    "name": "solve_challenge",
    "description": "Solves the exam challenge using the X-Exam-Challenge request header.",
    "inputSchema": {"type": "object", "properties": {}},
}

def answer(challenge: str) -> str:
    return hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]

def handle(msg: dict, headers):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:                       # notification (e.g. notifications/initialized)
        return None
    def ok(result): return {"jsonrpc": "2.0", "id": mid, "result": result}
    def err(code, m): return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": m}}

    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion", "2025-03-26")
        return ok({
            "protocolVersion": ver,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp", "version": "1.0.0"},
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [TOOL]})
    if method == "tools/call":
        if (msg.get("params") or {}).get("name") != "solve_challenge":
            return err(-32602, "Unknown tool")
        challenge = headers.get("x-exam-challenge", "").strip()
        if not challenge:
            return ok({"content": [{"type": "text", "text": "missing X-Exam-Challenge"}], "isError": True})
        return ok({"content": [{"type": "text", "text": answer(challenge)}]})
    return err(-32601, f"Method not found: {method}")

@app.post("/")
@app.post("/mcp")
async def mcp(request: Request):
    body = await request.json()
    if isinstance(body, list):
        out = [r for r in (handle(m, request.headers) for m in body) if r]
        return JSONResponse(out) if out else Response(status_code=202)
    res = handle(body, request.headers)
    return JSONResponse(res) if res else Response(status_code=202)

@app.get("/")
@app.get("/mcp")
async def not_allowed():
    return Response(status_code=405, headers={"Allow": "POST"})
