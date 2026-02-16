# ✅ 运行一次性迁移脚本
# 用法: python migrate_db.py

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "app" / "db" / "evaluator.db"

def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # ✅ 检查是否已有 provider 列
        cursor.execute("PRAGMA table_info(evaluations)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'provider' not in columns:
            print("✅ Adding 'provider' column...")
            cursor.execute("ALTER TABLE evaluations ADD COLUMN provider VARCHAR(20) DEFAULT 'gpt'")
            conn.commit()
            print("✅ 'provider' column added successfully!")
        else:
            print("ℹ️  'provider' column already exists.")
        
        # ✅ 检查是否已有新维度列
        if 'critical_pedagogy_score' not in columns:
            print("✅ Adding 'critical_pedagogy_score' column...")
            cursor.execute("ALTER TABLE evaluations ADD COLUMN critical_pedagogy_score INTEGER")
            conn.commit()
            print("✅ 'critical_pedagogy_score' column added!")
        
        if 'lesson_design_score' not in columns:
            print("✅ Adding 'lesson_design_score' column...")
            cursor.execute("ALTER TABLE evaluations ADD COLUMN lesson_design_score INTEGER")
            conn.commit()
            print("✅ 'lesson_design_score' column added!")
        
        print("\n🎉 Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()