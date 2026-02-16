
import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

# Database file path
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "evaluator.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

print(f"Debug: Script location: {__file__}")
print(f"Debug: DB path: {DB_PATH}")
print(f"Debug: Schema path: {SCHEMA_PATH}")


class Database:
    """SQLite database manager for lesson plan evaluations"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Create a database connection (allow cross-thread use)"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        """Close database connection"""
        if self.conn:
            try:
                self.conn.close()
            finally:
                self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def initialize_schema(self):
        """Initialize database schema from SQL file"""
        print(f"Looking for schema file: {SCHEMA_PATH}")
        if not SCHEMA_PATH.exists():
            print("Schema file not found!")
            raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

        print("Found schema file")
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        print("Executing SQL schema...")
        cursor = self.conn.cursor()
        cursor.executescript(schema_sql)
        self.conn.commit()
        print(f"Database initialized: {self.db_path}")

    # ==========================================
    # Evaluation CRUD Operations
    # ==========================================

    def create_evaluation(
        self,
        lesson_plan_text: str,
        lesson_plan_title: Optional[str] = None,
        grade_level: Optional[str] = None,
        subject_area: Optional[str] = None,
        place_based_score: int = 0,  # ✅ 新增
        cultural_score: int = 0,  # ✅ 新增
        critical_pedagogy_score: int = 0,  # ✅ 新增 v3.0
        lesson_design_score: int = 0,  # ✅ 新增 v3.0
        overall_score: int = 0,  # ✅ 新增
        agent_responses: List[Dict] = None,  # ✅ 新增
        recommendations: List[str] = None,  # ✅ 新增
        provider: str = "gpt",  # ✅ 新增 Ensemble mode
        api_mode: str = "mock"
    ) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO evaluations (
            lesson_plan_text,
            lesson_plan_title,
            grade_level,
            subject_area,
            place_based_score,
            cultural_score,
            critical_pedagogy_score,
            lesson_design_score,
            overall_score,
            agent_responses,
            recommendations,
            provider,
            api_mode,
            status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            """,
            (lesson_plan_text, lesson_plan_title, grade_level, subject_area, place_based_score, cultural_score, critical_pedagogy_score, lesson_design_score, overall_score, json.dumps(agent_responses) if agent_responses else None, json.dumps(recommendations) if recommendations else None, provider, api_mode)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_evaluation_status(self, eval_id: int, status: str):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE evaluations
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, eval_id)
        )
        self.conn.commit()

    def update_evaluation_scores(
        self,
        eval_id: int,
        place_based_score: int,
        cultural_score: int,
        overall_score: int
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE evaluations
            SET place_based_score = ?,
                cultural_score = ?,
                overall_score = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (place_based_score, cultural_score, overall_score, eval_id)
        )
        self.conn.commit()

    def update_evaluation_results(
        self,
        eval_id: int,
        agent_responses: List[Dict],
        debate_transcript: Dict,
        recommendations: List[str],
        status: str = "completed"
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE evaluations
            SET agent_responses = ?,
                debate_transcript = ?,
                recommendations = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                json.dumps(agent_responses),
                json.dumps(debate_transcript),
                json.dumps(recommendations),
                status,
                eval_id
            )
        )
        self.conn.commit()

    def get_evaluation(self, eval_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM evaluations WHERE id = ?", (eval_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_evaluations(self, limit: int = 50) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM evaluations
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_evaluations_by_status(self, status: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM evaluations
            WHERE status = ?
            ORDER BY created_at DESC
            """,
            (status,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==========================================
    # Debate Session CRUD Operations
    # ==========================================

    def create_debate_session(
        self,
        eval_id: int,
        round_number: int,
        topic: str,
        exchanges: List[Dict],
        duration_seconds: Optional[int] = None
    ) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO debate_sessions (
                evaluation_id,
                round_number,
                topic,
                exchanges,
                duration_seconds
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (eval_id, round_number, topic, json.dumps(exchanges), duration_seconds)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_debate_sessions(self, eval_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM debate_sessions
            WHERE evaluation_id = ?
            ORDER BY round_number
            """,
            (eval_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==========================================
    # Analytics Queries
    # ==========================================

    def get_statistics(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM evaluations")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as completed FROM evaluations WHERE status = 'completed'")
        completed = cursor.fetchone()["completed"]

        cursor.execute(
            """
            SELECT
                AVG(place_based_score) as avg_place_based,
                AVG(cultural_score) as avg_cultural,
                AVG(overall_score) as avg_overall
            FROM evaluations
            WHERE status = 'completed'
            """
        )
        scores_row = cursor.fetchone()
        scores = dict(scores_row) if scores_row else {
            "avg_place_based": None,
            "avg_cultural": None,
            "avg_overall": None
        }

        cursor.execute(
            """
            SELECT
                api_mode,
                COUNT(*) as count,
                AVG(overall_score) as avg_score
            FROM evaluations
            WHERE status = 'completed'
            GROUP BY api_mode
            """
        )
        by_api_mode = [dict(row) for row in cursor.fetchall()]

        return {
            "total_evaluations": total,
            "completed_evaluations": completed,
            "average_scores": scores,
            "by_api_mode": by_api_mode
        }

    def delete_evaluation(self, eval_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM evaluations WHERE id = ?", (eval_id,))
        self.conn.commit()


# ==========================================
# Initialization Function
# ==========================================

def init_database(reset: bool = False):
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)

    db = Database()
    db.connect()

    if reset:
        print("Resetting database (dropping all tables)...")

    try:
        db.initialize_schema()
        db.close()

        print(f"Database ready at: {DB_PATH}")
        if os.path.exists(DB_PATH):
            print(f"File size: {os.path.getsize(DB_PATH)} bytes")
        print("=" * 50)
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.close()
        raise


# ==========================================
# CLI for Database Management
# ==========================================

if __name__ == "__main__":
    import sys

    print("Python Database Manager")
    print(f"Working directory: {os.getcwd()}")
    print(f"Arguments: {sys.argv}")

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        reset = "--reset" in sys.argv
