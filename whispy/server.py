"""FastAPI HTTP+REST server for the Whispy Second Brain.

Exposes the HyperKanban tree, search, graph, backlinks, stats, and a tiny
markdown rendering endpoint. Mounted by :mod:`whispy.webapp` inside the
desktop window, and usable standalone via ``whispy serve``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from .store import Store


def create_app(store: Store | None = None, web_dir: Path | None = None) -> FastAPI:
    """Build and return a configured FastAPI application."""
    app = FastAPI(title="Whispy Brain", version="0.1.0", docs_url="/docs")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    state = store or Store()
    assets = web_dir or (Path(__file__).resolve().parent.parent / "web")

    register_static_routes(app, assets)
    register_api_routes(app, state)
    return app


def register_static_routes(app: FastAPI, web_dir: Path) -> None:
    """Serve the bundled single-page web UI."""

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        path = web_dir / "index.html"
        if path.exists():
            return HTMLResponse(path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Whispy Brain</h1><p>web/ not found</p>", status_code=404)

    @app.get("/styles.css")
    async def styles() -> Response:
        path = web_dir / "styles.css"
        if path.exists():
            return Response(content=path.read_text(encoding="utf-8"), media_type="text/css")
        return Response(status_code=404)

    @app.get("/main.js")
    async def main_js() -> Response:
        path = web_dir / "main.js"
        if path.exists():
            return Response(
                content=path.read_text(encoding="utf-8"), media_type="application/javascript"
            )
        return Response(status_code=404)

    @app.get("/favicon.ico")
    async def favicon() -> Response:
        for path in (web_dir / "favicon.ico", web_dir / "assets" / "favicon.ico"):
            if path.exists():
                return Response(content=path.read_bytes(), media_type="image/x-icon")
        return Response(status_code=404)


def register_api_routes(app: FastAPI, state: Store) -> None:
    """Wire CRUD/tree/search/graph/stats/backlinks endpoints."""

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "nodes": len(state.nodes)}

    @app.get("/api/tree")
    async def get_tree(root_id: str | None = None, max_depth: int = 10) -> list[dict]:
        return state.tree(root_id=root_id, max_depth=max_depth)

    @app.get("/api/nodes/{node_id}")
    async def get_node(node_id: str) -> dict:
        node = state.get(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="node not found")
        return state.tree(root_id=node_id, max_depth=10)[0]

    @app.post("/api/nodes")
    async def create_node(request: Request) -> dict:
        body = await request.json()
        node = state.create_node(**_filter_fields(body))
        return state.tree(root_id=node.id, max_depth=5)[0]

    @app.patch("/api/nodes/{node_id}")
    async def update_node(node_id: str, request: Request) -> dict:
        body = await request.json()
        node = state.update_node(node_id, **_filter_fields(body))
        return state.tree(root_id=node.id, max_depth=5)[0]

    @app.delete("/api/nodes/{node_id}")
    async def delete_node(node_id: str, keep_children: bool = False) -> dict:
        state.delete_node(node_id, delete_children=not keep_children)
        return {"ok": True}

    @app.post("/api/nodes/{node_id}/move")
    async def move_node(node_id: str, request: Request) -> dict:
        body = await request.json()
        node = state.move_node(
            node_id,
            body.get("parent_id"),
            body.get("position"),
        )
        return state.tree(root_id=node.id, max_depth=5)[0]

    @app.post("/api/nodes/{node_id}/indent")
    async def indent_node(node_id: str, request: Request) -> dict:
        body = await request.json()
        direction = body.get("direction", "indent")
        node = state.indent(node_id, direction)
        return state.tree(root_id=node.id, max_depth=5)[0]

    @app.post("/api/nodes/{node_id}/toggle")
    async def toggle_status(node_id: str) -> dict:
        node = state.toggle_status(node_id)
        return state.tree(root_id=node.id, max_depth=5)[0]

    @app.get("/api/search")
    async def search(q: str = "", limit: int = 50) -> dict:
        return {"results": state.search(q, limit=limit)}

    @app.get("/api/graph")
    async def graph() -> dict:
        return state.graph()

    @app.get("/api/backlinks/{node_id}")
    async def backlinks(node_id: str) -> dict:
        return {"results": state.backlinks(node_id)}

    @app.get("/api/stats")
    async def stats() -> dict:
        s = state.stats()
        return {
            "total": s.total,
            "by_status": s.by_status,
            "by_priority": s.by_priority,
            "by_type": s.by_type,
            "overdue": s.overdue,
        }

    @app.post("/api/ingest")
    async def ingest(request: Request) -> dict:
        """Ingest transcribed text as a new note (bridge from dictation → brain)."""
        body = await request.json()
        text = (body.get("text") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text required")
        title = text.splitlines()[0][:80] if text else "Voice note"
        markdown = text
        parent_id = body.get("parent_id")
        node = state.create_node(
            title=title,
            node_type="note",
            body_markdown=markdown,
            parent_id=parent_id,
            tags=body.get("tags", ["voice"]),
        )
        return state.tree(root_id=node.id, max_depth=5)[0]


def _filter_fields(body: dict) -> dict:
    """Pick only known Node fields so we never inject extra kwargs."""
    allowed = {
        "parent_id",
        "title",
        "description",
        "icon",
        "color",
        "node_type",
        "status",
        "priority",
        "position",
        "due_date",
        "start_date",
        "completed_at",
        "tags",
        "body_markdown",
    }
    return {key: value for key, value in body.items() if key in allowed}


def run(host: str = "127.0.0.1", port: int = 58182) -> None:
    """Standalone server entrypoint (used by the ``serve`` subcommand)."""
    import uvicorn

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")
