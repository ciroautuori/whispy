"""In-memory + disk-persisted tree store for the Whispy Second Brain.

Models a HyperKanban tree: nodes nest infinitely and carry status, priority,
tags, due dates, backlinks, and markdown notes. Inspired by Notion (databases
/ properties / kanban) and Obsidian (markdown notes / backlinks / graph) and
by the HyperTask domain spec.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC
from pathlib import Path

# ── Enums (string-valued for JSON friendliness) ────────────────────────────

NODE_TYPES = ("workspace", "area", "board", "task", "subtask", "note")
STATUSES = ("todo", "in_progress", "review", "done")
PRIORITIES = ("none", "low", "medium", "high", "urgent")


# ── Data model ──────────────────────────────────────────────────────────────


@dataclass
class Node:
    """A single node in the HyperKanban tree."""

    id: str
    parent_id: str | None = None
    title: str = ""
    description: str = ""
    icon: str = ""
    color: str = ""
    node_type: str = "task"  # one of NODE_TYPES
    status: str = "todo"  # one of STATUSES
    priority: str = "none"  # one of PRIORITIES
    position: float = 0.0  # float for fractional ordering
    due_date: str | None = None
    start_date: str | None = None
    completed_at: str | None = None
    tags: list[str] = field(default_factory=list)
    body_markdown: str = ""  # Obsidian-style note body
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    children: list[str] = field(default_factory=list)


@dataclass
class TreeStats:
    """Aggregate statistics over the tree."""

    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    by_priority: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    overdue: int = 0


# ── Store ──────────────────────────────────────────────────────────────────


class Store:
    """JSON-backed tree store with O(1) id lookups.

    The whole tree is persisted as a single JSON file (default
    ``~/.local/share/whispy/brain.json``). Loading and saving is cheap for
    a personal second-brain dataset (tens of thousands of nodes).
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else self._default_path()
        self.nodes: dict[str, Node] = {}
        self.roots: list[str] = []
        self._load()

    @staticmethod
    def _default_path() -> Path:
        import os

        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) / "whispy" if xdg else Path.home() / ".local" / "share" / "whispy"
        base.mkdir(parents=True, exist_ok=True)
        return base / "brain.json"

    # ── persistence ─────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.path.exists():
            self._seed_demo()
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._seed_demo()
            return
        for node_id, raw in data.get("nodes", {}).items():
            raw.pop("children", None)
            self.nodes[node_id] = Node(**raw)
        self._rebuild_children()
        self._recompute_roots()

    def save(self) -> None:
        """Persist the entire tree to disk."""
        payload = {"nodes": {nid: asdict(n) for nid, n in self.nodes.items()}}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def _rebuild_children(self) -> None:
        for n in self.nodes.values():
            n.children = []
        for n in self.nodes.values():
            if n.parent_id and n.parent_id in self.nodes:
                self.nodes[n.parent_id].children.append(n.id)

    def _recompute_roots(self) -> None:
        self.roots = [
            n.id
            for n in self.nodes.values()
            if n.parent_id is None or n.parent_id not in self.nodes
        ]
        self.roots.sort(key=lambda nid: self.nodes[nid].position)

    def _seed_demo(self) -> None:
        """Seed a small demo workspace so the UI is not empty on first run."""
        ws = self.create_node(title="My Brain", node_type="workspace")
        area = self.create_node(parent_id=ws.id, title="Work", node_type="area")
        board = self.create_node(parent_id=area.id, title="Sprint 1", node_type="board")
        self.create_node(
            parent_id=board.id,
            title="Ship whispy v0.1",
            node_type="task",
            status="in_progress",
            priority="high",
            tags=["release"],
        )
        self.create_node(
            parent_id=board.id,
            title="Write README",
            node_type="task",
            status="todo",
            priority="medium",
        )
        notes = self.create_node(parent_id=ws.id, title="Notes", node_type="area")
        self.create_node(
            parent_id=notes.id,
            title="Welcome",
            node_type="note",
            body_markdown=(
                "# Welcome to Whispy Brain\n\n"
                "This is a hybrid of **Notion** (kanban + properties) and "
                "**Obsidian** (markdown + [[backlinks]]).\n\n"
                "- `Super+F12` records your voice → transcribed here.\n"
                "- Tasks nest infinitely (HyperKanban).\n"
                "- Link nodes with [[wikilinks]] — backlinks appear automatically."
            ),
        )
        self.save()

    # ── mutations ───────────────────────────────────────────────────────────

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    def create_node(self, **fields) -> Node:
        """Create and attach a new node. Returns the node."""
        node_id = fields.pop("id", None) or self._new_id()
        node = Node(id=node_id, **fields)
        if node.parent_id and node.parent_id in self.nodes:
            siblings = self.nodes[node.parent_id].children
            node.position = max((self.nodes[sid].position for sid in siblings), default=0.0) + 1.0
        node.updated_at = time.time()
        self.nodes[node_id] = node
        if node.parent_id and node.parent_id in self.nodes:
            self.nodes[node.parent_id].children.append(node_id)
        else:
            self._recompute_roots()
        self.save()
        return node

    def update_node(self, node_id: str, **fields) -> Node:
        """Patch a node's fields and persist."""
        node = self._require(node_id)
        for key, value in fields.items():
            if hasattr(node, key) and key != "id":
                setattr(node, key, value)
        node.updated_at = time.time()
        self.save()
        return node

    def delete_node(self, node_id: str, *, delete_children: bool = True) -> None:
        """Delete a node and (optionally) its subtree."""
        node = self._require(node_id)
        children = list(node.children)
        if delete_children:
            for child_id in children:
                self.delete_node(child_id)
        elif children:
            # Promote children to the deleted node's parent
            for child_id in children:
                self.nodes[child_id].parent_id = node.parent_id
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node_id in parent.children:
                parent.children.remove(node_id)
        del self.nodes[node_id]
        self._recompute_roots()
        self.save()

    def move_node(
        self,
        node_id: str,
        new_parent_id: str | None,
        new_position: float | None = None,
    ) -> Node:
        """Re-parent and optionally re-order a node."""
        node = self._require(node_id)
        if new_parent_id == node_id or (
            new_parent_id and self._is_descendant(new_parent_id, node_id)
        ):
            raise ValueError("cannot move a node into itself or its subtree")
        # detach from old parent
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node_id in parent.children:
                parent.children.remove(node_id)
        node.parent_id = new_parent_id
        if new_parent_id and new_parent_id in self.nodes:
            self.nodes[new_parent_id].children.append(node_id)
        if new_position is not None:
            node.position = new_position
        elif new_parent_id and new_parent_id in self.nodes:
            siblings = self.nodes[new_parent_id].children
            node.position = (
                max(
                    (self.nodes[sid].position for sid in siblings if sid != node_id),
                    default=0.0,
                )
                + 1.0
            )
        node.updated_at = time.time()
        self._recompute_roots()
        self.save()
        return node

    def toggle_status(self, node_id: str) -> Node:
        """Cycle a task through todo → in_progress → done → todo."""
        node = self._require(node_id)
        cycle = {"todo": "in_progress", "in_progress": "done", "done": "todo"}
        node.status = cycle.get(node.status, "todo")
        if node.status == "done":
            node.completed_at = _now_iso()
        else:
            node.completed_at = None
        node.updated_at = time.time()
        self.save()
        return node

    def indent(self, node_id: str, direction: str) -> Node:
        """Indent (make child of previous sibling) or outdent (promote)."""
        node = self._require(node_id)
        if direction == "indent":
            siblings = self._siblings_of(node)
            idx = siblings.index(node_id)
            if idx <= 0:
                return node
            new_parent_id = siblings[idx - 1]
            return self.move_node(node_id, new_parent_id)
        if direction == "outdent":
            if not node.parent_id:
                return node
            grandparent = self.nodes[node.parent_id].parent_id
            return self.move_node(node_id, grandparent)
        return node

    # ── queries ─────────────────────────────────────────────────────────────

    def get(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def tree(self, root_id: str | None = None, max_depth: int = 10) -> list[dict]:
        """Return nested node dicts (with children) for serialization."""
        top_ids = [root_id] if root_id else self.roots
        return [self._node_to_dict(nid, depth=max_depth) for nid in top_ids]

    def stats(self) -> TreeStats:
        """Compute aggregate statistics."""
        stats = TreeStats(total=len(self.nodes))
        now = _now_iso()
        for node in self.nodes.values():
            stats.by_status[node.status] = stats.by_status.get(node.status, 0) + 1
            stats.by_priority[node.priority] = stats.by_priority.get(node.priority, 0) + 1
            stats.by_type[node.node_type] = stats.by_type.get(node.node_type, 0) + 1
            if node.due_date and node.due_date < now and node.status != "done":
                stats.overdue += 1
        return stats

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Full-text search over titles, descriptions, tags, and markdown bodies."""
        text_query = query.lower().strip()
        if not text_query:
            return []
        results: list[dict] = []
        for node in self.nodes.values():
            haystack = " ".join(
                [node.title, node.description, " ".join(node.tags), node.body_markdown]
            ).lower()
            if text_query in haystack:
                results.append(self._node_to_dict(node.id))
                if len(results) >= limit:
                    break
        return results

    def backlinks(self, target_id: str) -> list[dict]:
        """Return nodes whose markdown body links to ``target_id`` via [[wikilinks]]."""
        import re

        target = self.nodes.get(target_id)
        if not target:
            return []
        pattern = re.compile(r"\[\[([^\]]+)\]\]")
        matches: list[dict] = []
        for node in self.nodes.values():
            if node.id == target_id:
                continue
            for link in pattern.findall(node.body_markdown):
                if link.strip().lower() == target.title.strip().lower() or link == target_id:
                    matches.append(self._node_to_dict(node.id))
                    break
        return matches

    def graph(self) -> dict:
        """Return nodes + edges for the backlink graph view (Obsidian-style)."""
        import re

        pattern = re.compile(r"\[\[([^\]]+)\]\]")
        nodes = [
            {"id": n.id, "label": n.title, "type": n.node_type, "status": n.status}
            for n in self.nodes.values()
        ]
        edges: list[dict] = []
        by_title = {n.title.strip().lower(): n.id for n in self.nodes.values() if n.title}
        for node in self.nodes.values():
            for link in pattern.findall(node.body_markdown):
                target_id = by_title.get(link.strip().lower()) or link
                if target_id in self.nodes:
                    edges.append({"source": node.id, "target": target_id})
        return {"nodes": nodes, "edges": edges}

    # ── helpers ────────────────────────────────────────────────────────────

    def _require(self, node_id: str) -> Node:
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"node not found: {node_id}")
        return node

    def _siblings_of(self, node: Node) -> list[str]:
        if node.parent_id and node.parent_id in self.nodes:
            return self.nodes[node.parent_id].children
        return self.roots

    def _is_descendant(self, candidate_id: str, ancestor_id: str) -> bool:
        current = self.nodes.get(candidate_id)
        while current and current.parent_id:
            if current.parent_id == ancestor_id:
                return True
            current = self.nodes.get(current.parent_id)
        return False

    def _node_to_dict(self, node_id: str, *, depth: int = 0) -> dict:
        node = self.nodes[node_id]
        children: list[dict] = []
        if depth > 0:
            children.extend(
                sorted(
                    (self._node_to_dict(child_id, depth=depth - 1) for child_id in node.children),
                    key=lambda child: child.get("position", 0),
                )
            )
        return {
            "id": node.id,
            "parent_id": node.parent_id,
            "title": node.title,
            "description": node.description,
            "icon": node.icon,
            "color": node.color,
            "node_type": node.node_type,
            "status": node.status,
            "priority": node.priority,
            "position": node.position,
            "due_date": node.due_date,
            "start_date": node.start_date,
            "completed_at": node.completed_at,
            "tags": list(node.tags),
            "body_markdown": node.body_markdown,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
            "children": children,
            "children_count": len(node.children),
        }


def _now_iso() -> str:
    """Return an ISO 8601 timestamp for the current instant."""
    from datetime import datetime

    return datetime.now(UTC).isoformat()
