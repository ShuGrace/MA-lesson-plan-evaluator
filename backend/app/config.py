import os
from dotenv import load_dotenv

# 只在本地开发时加载 .env 文件
if os.path.exists(".env.development"):
    load_dotenv(".env.development")
    print("[Config] Loaded .env.development")
elif os.path.exists(".env"):
    load_dotenv(".env")
    print("[Config] Loaded .env")
else:
    print("[Config] Using environment variables (production mode)")

# API mode: "mock" for development, "real" for production/testing
API_MODE = os.getenv("API_MODE", "real")

# API Keys
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

# Model configurations
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# API settings
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "120"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    # 如果 Railway 提供的是 postgres://，需要改为 postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
# Debug print - 可以在生产环境保留，方便排查问题
print(f"[Config] API_MODE={API_MODE}, DB={DATABASE_URL}")
print(f"[Config] Database={DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL}")
print(f"[Config] OpenAI Key: {'✅ Set' if OPENAI_KEY else '❌ Missing'}")
print(f"[Config] ANTHROPIC Key: {'✅ Set' if ANTHROPIC_KEY else '❌ Missing'}")
print(f"[Config] DeepSeek Key: {'✅ Set' if DEEPSEEK_KEY else '❌ Missing'}")

# ⚠️ 生产环境建议移除密钥前缀显示（安全考虑）
# 可以用环境变量控制是否显示
if os.getenv("DEBUG_MODE", "false").lower() == "true":
    if OPENAI_KEY:
        print(f"[Config] OpenAI Key prefix: {OPENAI_KEY[:10]}...")
    if ANTHROPIC_KEY:
        print(f"[Config] ANTHROPIC Key prefix: {ANTHROPIC_KEY[:10]}...")
    if DEEPSEEK_KEY:
        print(f"[Config] DeepSeek Key prefix: {DEEPSEEK_KEY[:10]}...")