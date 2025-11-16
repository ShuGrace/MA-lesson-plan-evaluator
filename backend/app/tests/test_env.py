# 测试所有依赖是否安装成功
try:
    import fastapi
    print("✅ FastAPI:", fastapi.__version__)
except ImportError:
    print("❌ FastAPI 未安装")

try:
    import uvicorn
    print("✅ Uvicorn:", uvicorn.__version__)
except ImportError:
    print("❌ Uvicorn 未安装")

try:
    import sqlalchemy
    print("✅ SQLAlchemy:", sqlalchemy.__version__)
except ImportError:
    print("❌ SQLAlchemy 未安装")

try:
    import sqlite3
    print("✅ SQLite3:", sqlite3.sqlite_version)
except ImportError:
    print("❌ SQLite3 不可用")

print("\n🎉 所有依赖就绪！")