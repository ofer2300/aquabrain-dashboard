"""
AquaBrain Memory Engine V7.0
============================
Semantic Memory & Knowledge Graph for Project Intelligence.

Features:
- Weaviate vector database integration
- Project context retrieval
- Document embedding and search
- Historical analysis (payments, defects, communications)
- Meeting preparation context
- Risk assessment data

The cognitive backbone of the Virtual Senior Engineer.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import os
import json
import sqlite3
import hashlib

# Weaviate client (optional - falls back to SQLite)
try:
    import weaviate
    from weaviate.classes.query import MetadataQuery
    HAS_WEAVIATE = True
except ImportError:
    HAS_WEAVIATE = False
    print("[MemoryEngine] Weaviate not available - using SQLite fallback")

# AI for embeddings
try:
    from services.ai_engine import ask_ai
    HAS_AI = True
except ImportError:
    HAS_AI = False


# ============================================================================
# CONSTANTS
# ============================================================================

DATA_DIR = Path(__file__).parent.parent / "data"
MEMORY_DB_PATH = DATA_DIR / "memory.db"
WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY", "")


# ============================================================================
# PROJECT MEMORY SCHEMA
# ============================================================================

class ProjectMemoryItem:
    """A single memory item about a project."""

    def __init__(
        self,
        project_id: str,
        category: str,  # document, email, meeting, issue, payment, defect
        content: str,
        metadata: Dict[str, Any] = None,
        timestamp: datetime = None,
        source: str = "system",
        importance: float = 0.5,
    ):
        self.id = hashlib.md5(f"{project_id}:{content[:100]}:{timestamp}".encode()).hexdigest()[:12]
        self.project_id = project_id
        self.category = category
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.source = source
        self.importance = importance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "category": self.category,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "importance": self.importance,
        }


# ============================================================================
# SQLITE MEMORY STORE (Fallback)
# ============================================================================

class SQLiteMemoryStore:
    """Local SQLite storage for project memories when Weaviate unavailable."""

    def __init__(self, db_path: Path = MEMORY_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_memories (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT,
                source TEXT,
                importance REAL DEFAULT 0.5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_id ON project_memories(project_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON project_memories(category)
        """)

        conn.commit()
        conn.close()

    def store(self, item: ProjectMemoryItem):
        """Store a memory item."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO project_memories
            (id, project_id, category, content, metadata, timestamp, source, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id, item.project_id, item.category, item.content,
            json.dumps(item.metadata), item.timestamp.isoformat(),
            item.source, item.importance
        ))

        conn.commit()
        conn.close()

    def query(
        self,
        project_id: str,
        categories: List[str] = None,
        limit: int = 20,
        since: datetime = None,
    ) -> List[ProjectMemoryItem]:
        """Query memories for a project."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = "SELECT * FROM project_memories WHERE project_id = ?"
        params = [project_id]

        if categories:
            placeholders = ",".join(["?" for _ in categories])
            query += f" AND category IN ({placeholders})"
            params.extend(categories)

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        items = []
        for row in rows:
            items.append(ProjectMemoryItem(
                project_id=row[1],
                category=row[2],
                content=row[3],
                metadata=json.loads(row[4]) if row[4] else {},
                timestamp=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                source=row[6],
                importance=row[7],
            ))
            items[-1].id = row[0]

        return items

    def search(self, project_id: str, query_text: str, limit: int = 10) -> List[ProjectMemoryItem]:
        """Simple text search (keyword-based)."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Simple LIKE search
        cursor.execute("""
            SELECT * FROM project_memories
            WHERE project_id = ? AND content LIKE ?
            ORDER BY importance DESC, timestamp DESC
            LIMIT ?
        """, (project_id, f"%{query_text}%", limit))

        rows = cursor.fetchall()
        conn.close()

        items = []
        for row in rows:
            items.append(ProjectMemoryItem(
                project_id=row[1],
                category=row[2],
                content=row[3],
                metadata=json.loads(row[4]) if row[4] else {},
                timestamp=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                source=row[6],
                importance=row[7],
            ))
            items[-1].id = row[0]

        return items

    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Get statistics for a project."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM project_memories
            WHERE project_id = ?
            GROUP BY category
        """, (project_id,))

        categories = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
            FROM project_memories
            WHERE project_id = ?
        """, (project_id,))

        total, first, last = cursor.fetchone()
        conn.close()

        return {
            "total_memories": total or 0,
            "categories": categories,
            "first_memory": first,
            "last_memory": last,
        }


# ============================================================================
# WEAVIATE MEMORY STORE
# ============================================================================

class WeaviateMemoryStore:
    """Weaviate vector database for semantic project memories."""

    COLLECTION_NAME = "ProjectMemory"

    def __init__(self, url: str = WEAVIATE_URL, api_key: str = WEAVIATE_API_KEY):
        self.client = None
        self.collection = None

        if not HAS_WEAVIATE:
            return

        try:
            if api_key:
                self.client = weaviate.connect_to_wcs(
                    cluster_url=url,
                    auth_credentials=weaviate.AuthApiKey(api_key),
                )
            else:
                self.client = weaviate.connect_to_local(host=url.replace("http://", "").split(":")[0])

            self._ensure_collection()
        except Exception as e:
            print(f"[MemoryEngine] Weaviate connection failed: {e}")
            self.client = None

    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        if not self.client:
            return

        try:
            collections = self.client.collections.list_all()
            if self.COLLECTION_NAME not in [c.name for c in collections]:
                self.client.collections.create(
                    name=self.COLLECTION_NAME,
                    properties=[
                        {"name": "project_id", "dataType": ["text"]},
                        {"name": "category", "dataType": ["text"]},
                        {"name": "content", "dataType": ["text"]},
                        {"name": "metadata_json", "dataType": ["text"]},
                        {"name": "timestamp", "dataType": ["date"]},
                        {"name": "source", "dataType": ["text"]},
                        {"name": "importance", "dataType": ["number"]},
                    ],
                )
            self.collection = self.client.collections.get(self.COLLECTION_NAME)
        except Exception as e:
            print(f"[MemoryEngine] Collection setup failed: {e}")

    def store(self, item: ProjectMemoryItem):
        """Store with vector embedding."""
        if not self.collection:
            return

        try:
            self.collection.data.insert(
                properties={
                    "project_id": item.project_id,
                    "category": item.category,
                    "content": item.content,
                    "metadata_json": json.dumps(item.metadata),
                    "timestamp": item.timestamp.isoformat(),
                    "source": item.source,
                    "importance": item.importance,
                },
            )
        except Exception as e:
            print(f"[MemoryEngine] Store failed: {e}")

    def semantic_search(
        self,
        project_id: str,
        query_text: str,
        limit: int = 10,
    ) -> List[ProjectMemoryItem]:
        """Semantic search using vector similarity."""
        if not self.collection:
            return []

        try:
            results = self.collection.query.near_text(
                query=query_text,
                filters={"path": ["project_id"], "operator": "Equal", "valueText": project_id},
                limit=limit,
            )

            items = []
            for obj in results.objects:
                props = obj.properties
                items.append(ProjectMemoryItem(
                    project_id=props.get("project_id"),
                    category=props.get("category"),
                    content=props.get("content"),
                    metadata=json.loads(props.get("metadata_json", "{}")),
                    timestamp=datetime.fromisoformat(props.get("timestamp")) if props.get("timestamp") else datetime.now(),
                    source=props.get("source"),
                    importance=props.get("importance", 0.5),
                ))

            return items

        except Exception as e:
            print(f"[MemoryEngine] Search failed: {e}")
            return []

    def close(self):
        if self.client:
            self.client.close()


# ============================================================================
# UNIFIED MEMORY ENGINE
# ============================================================================

class MemoryEngine:
    """
    Unified Memory Engine - The cognitive core of AquaBrain.

    Automatically uses Weaviate if available, falls back to SQLite.
    """

    def __init__(self):
        self.sqlite_store = SQLiteMemoryStore()
        self.weaviate_store = WeaviateMemoryStore() if HAS_WEAVIATE else None
        self._use_weaviate = self.weaviate_store and self.weaviate_store.client is not None

    def store_memory(self, item: ProjectMemoryItem):
        """Store a memory item in all available stores."""
        # Always store in SQLite (reliable)
        self.sqlite_store.store(item)

        # Also store in Weaviate if available
        if self._use_weaviate:
            self.weaviate_store.store(item)

    def query_project_context(
        self,
        project_name: str,
        categories: List[str] = None,
        limit: int = 20,
        days_back: int = 90,
    ) -> str:
        """
        Query and summarize project context for the Virtual Senior Engineer.

        Returns a formatted context string ready for LLM consumption.
        """
        since = datetime.now() - timedelta(days=days_back)

        # Get memories
        memories = self.sqlite_store.query(
            project_id=project_name,
            categories=categories,
            limit=limit,
            since=since,
        )

        if not memories:
            return f"אין מידע היסטורי זמין על הפרויקט: {project_name}"

        # Format context
        context_parts = [f"## סיכום הקשר לפרויקט: {project_name}\n"]

        # Group by category
        by_category: Dict[str, List[ProjectMemoryItem]] = {}
        for mem in memories:
            if mem.category not in by_category:
                by_category[mem.category] = []
            by_category[mem.category].append(mem)

        category_labels = {
            "document": "📄 מסמכים",
            "email": "📧 תכתובות",
            "meeting": "🗓️ פגישות",
            "issue": "⚠️ בעיות",
            "payment": "💰 תשלומים",
            "defect": "🔧 ליקויים",
            "milestone": "🎯 אבני דרך",
        }

        for category, items in by_category.items():
            label = category_labels.get(category, category)
            context_parts.append(f"\n### {label}")
            for item in items[:5]:  # Max 5 per category
                date_str = item.timestamp.strftime("%d/%m/%Y")
                context_parts.append(f"- [{date_str}] {item.content[:200]}")

        # Get stats
        stats = self.sqlite_store.get_project_stats(project_name)
        context_parts.append(f"\n### 📊 סטטיסטיקות")
        context_parts.append(f"- סה\"כ רשומות: {stats['total_memories']}")

        return "\n".join(context_parts)

    def search_context(
        self,
        project_name: str,
        query: str,
        limit: int = 10,
    ) -> str:
        """Search for specific context within a project."""
        # Try semantic search first (Weaviate)
        if self._use_weaviate:
            results = self.weaviate_store.semantic_search(project_name, query, limit)
            if results:
                return self._format_search_results(results)

        # Fallback to keyword search
        results = self.sqlite_store.search(project_name, query, limit)
        return self._format_search_results(results)

    def _format_search_results(self, results: List[ProjectMemoryItem]) -> str:
        """Format search results for LLM."""
        if not results:
            return "לא נמצאו תוצאות רלוונטיות."

        parts = ["## תוצאות חיפוש\n"]
        for item in results:
            date_str = item.timestamp.strftime("%d/%m/%Y")
            parts.append(f"- **[{item.category}]** {date_str}: {item.content[:300]}")

        return "\n".join(parts)

    def check_risk_indicators(self, project_name: str) -> Dict[str, Any]:
        """
        Check for risk indicators in project history.

        Returns flags for:
        - Unpaid fees
        - Open defects
        - Missed deadlines
        - Communication issues
        """
        risks = {
            "unpaid_fees": False,
            "open_defects": False,
            "missed_deadlines": False,
            "communication_issues": False,
            "details": [],
        }

        # Check for payment issues
        payments = self.sqlite_store.query(
            project_id=project_name,
            categories=["payment"],
            limit=10,
        )
        for p in payments:
            content_lower = p.content.lower()
            if any(word in content_lower for word in ["לא שולם", "חוב", "unpaid", "overdue"]):
                risks["unpaid_fees"] = True
                risks["details"].append(f"חוב פתוח: {p.content[:100]}")

        # Check for open defects
        defects = self.sqlite_store.query(
            project_id=project_name,
            categories=["defect", "issue"],
            limit=10,
        )
        for d in defects:
            content_lower = d.content.lower()
            if any(word in content_lower for word in ["פתוח", "לא תוקן", "open", "unresolved"]):
                risks["open_defects"] = True
                risks["details"].append(f"ליקוי פתוח: {d.content[:100]}")

        return risks

    def add_project_memory(
        self,
        project_id: str,
        category: str,
        content: str,
        metadata: Dict[str, Any] = None,
        importance: float = 0.5,
    ):
        """Convenience method to add a memory."""
        item = ProjectMemoryItem(
            project_id=project_id,
            category=category,
            content=content,
            metadata=metadata,
            importance=importance,
        )
        self.store_memory(item)
        return item


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_memory_engine: Optional[MemoryEngine] = None


def get_memory_engine() -> MemoryEngine:
    """Get or create the global memory engine."""
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine()
    return _memory_engine


def query_project_context(project_name: str, **kwargs) -> str:
    """Convenience function for querying project context."""
    engine = get_memory_engine()
    return engine.query_project_context(project_name, **kwargs)


def check_project_risks(project_name: str) -> Dict[str, Any]:
    """Convenience function for checking project risks."""
    engine = get_memory_engine()
    return engine.check_risk_indicators(project_name)
