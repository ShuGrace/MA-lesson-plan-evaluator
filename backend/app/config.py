# app/config.py
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

# ============================================================
# API Mode
# ============================================================
API_MODE = os.getenv("API_MODE", "real")  # "mock" or "real"

# ============================================================
# API Keys
# ============================================================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

# ============================================================
# Model Configurations
# ============================================================
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ============================================================
# Framework Configuration
# ============================================================
FRAMEWORK_VERSION = "3.0"
FRAMEWORK_FILE = "theoretical_framework.json"
AGENT_DESIGN_FILE = "agent_design.json"

# ============================================================
# API Enable/Disable Switches (Framework )
# ============================================================
ENABLE_DEEPSEEK = os.getenv("ENABLE_DEEPSEEK", "true").lower() == "true"
ENABLE_CLAUDE = os.getenv("ENABLE_CLAUDE", "true").lower() == "true"
ENABLE_GPT = os.getenv("ENABLE_GPT", "true").lower() == "true"

# ============================================================
# API Timeout and Retry Configuration (Framework )
# ============================================================
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "180"))  # seconds
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "5"))
API_RETRY_DELAY = int(os.getenv("API_RETRY_DELAY", "15"))  # seconds

# Continue evaluation even if some APIs fail
CONTINUE_ON_API_FAILURE = os.getenv("CONTINUE_ON_API_FAILURE", "true").lower() == "true"

# ============================================================
# Database Configuration
# ============================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# 如果 Railway 提供的是 postgres://，需要改为 postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ============================================================
# Logging & Debug
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
DEBUG_API_CALLS = os.getenv("DEBUG_API_CALLS", "false").lower() == "true"

# ============================================================
# Startup Information
# ============================================================
print(f"[Config] ============================================================")
print(f"[Config] Framework Loaded")
print(f"[Config] API Mode: {API_MODE}")
print(f"[Config] Database: {DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL}")
print(f"[Config] ============================================================")

# API Keys Status
print(f"[Config] API Keys Status:")
print(f"  - OpenAI:    {'✅ Set' if OPENAI_KEY else '❌ Missing'}")
print(f"  - Anthropic: {'✅ Set' if ANTHROPIC_KEY else '❌ Missing'}")
print(f"  - DeepSeek:  {'✅ Set' if DEEPSEEK_KEY else '❌ Missing'}")

# API Switches Status
print(f"[Config] API Switches :")
print(f"  - DeepSeek: {'✅ Enabled' if ENABLE_DEEPSEEK else '⚠️  Disabled'}")
print(f"  - Claude:   {'✅ Enabled' if ENABLE_CLAUDE else '⚠️  Disabled'}")
print(f"  - GPT:      {'✅ Enabled' if ENABLE_GPT else '⚠️  Disabled'}")

# API Configuration
print(f"[Config] API Configuration:")
print(f"  - Timeout: {API_TIMEOUT}s")
print(f"  - Max Retries: {API_MAX_RETRIES}")
print(f"  - Retry Delay: {API_RETRY_DELAY}s")
print(f"  - Continue on Failure: {CONTINUE_ON_API_FAILURE}")
print(f"[Config] ============================================================")

# ⚠️ Debug Mode - 仅在开发环境显示密钥前缀
if DEBUG_MODE:
    print(f"[Config] DEBUG MODE - API Key Prefixes:")
    if OPENAI_KEY:
        print(f"  - OpenAI: {OPENAI_KEY[:15]}...")
    if ANTHROPIC_KEY:
        print(f"  - Anthropic: {ANTHROPIC_KEY[:15]}...")
    if DEEPSEEK_KEY:
        print(f"  - DeepSeek: {DEEPSEEK_KEY[:15]}...")
    print(f"[Config] ============================================================")