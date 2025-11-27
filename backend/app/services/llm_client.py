# app/services/llm_client.py
"""
LLM Client - Framework v3.0
✅ 4 Agents: DeepSeek (PBL), Claude (CRMP), GPT-Critical (CP), GPT-Design (LDQ)
"""
import asyncio
import json
from typing import Optional
from app.config import (
    API_MODE, OPENAI_KEY, ANTHROPIC_KEY, DEEPSEEK_KEY,
    OPENAI_MODEL, ANTHROPIC_MODEL, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL,
    API_TIMEOUT, API_MAX_RETRIES, ENABLE_DEEPSEEK, ENABLE_CLAUDE, ENABLE_GPT
)


class LLMClient:
    """
    Unified LLM Client for Multi-Model Support - Framework v3.0
    
    Agents (v3.0):
    - DeepSeek: Place-Based Learning Specialist (PBL)
    - Claude: Cultural Responsiveness & Māori Perspectives Specialist (CRMP - Integrated)
    - GPT (chatgpt): Shared for Critical Pedagogy (CP) and Lesson Design Quality (LDQ)
    """
    
    def __init__(self):
        self.timeout = API_TIMEOUT
        self.max_retries = API_MAX_RETRIES
        self._init_clients()
    
    def _init_clients(self):
        """Initialize all LLM clients with error handling"""
        print(f"\n[LLM] Initializing clients (Framework v3.0)...")
        
        # ==========================================
        # GPT (OpenAI) - for GPT-Critical and GPT-Design
        # ==========================================
        if OPENAI_KEY and ENABLE_GPT:
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=OPENAI_KEY, timeout=self.timeout)
                print("[LLM] ✅ GPT initialized (Critical Pedagogy & Lesson Design Quality)")
            except ImportError:
                print("[LLM] ❌ WARNING: openai package not installed")
                self.openai_client = None
            except Exception as e:
                print(f"[LLM] ❌ Failed to initialize GPT: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            if not OPENAI_KEY:
                print("[LLM] ⚠️  GPT not configured (no OPENAI_API_KEY)")
            elif not ENABLE_GPT:
                print("[LLM] ⚠️  GPT disabled (ENABLE_GPT=false)")
        
        # ==========================================
        # Claude (Anthropic) - for CRMP (Integrated)
        # ==========================================
        if ANTHROPIC_KEY and ENABLE_CLAUDE:
            try:
                from anthropic import AsyncAnthropic
                self.claude_client = AsyncAnthropic(api_key=ANTHROPIC_KEY, timeout=self.timeout)
                print("[LLM] ✅ Claude initialized (Cultural Responsiveness & Māori Perspectives - Integrated)")
            except ImportError:
                print("[LLM] ❌ WARNING: anthropic package not installed")
                self.claude_client = None
            except Exception as e:
                print(f"[LLM] ❌ Failed to initialize Claude: {e}")
                self.claude_client = None
        else:
            self.claude_client = None
            if not ANTHROPIC_KEY:
                print("[LLM] ⚠️  Claude not configured (no ANTHROPIC_API_KEY)")
            elif not ENABLE_CLAUDE:
                print("[LLM] ⚠️  Claude disabled (ENABLE_CLAUDE=false)")
        
        # ==========================================
        # DeepSeek - for Place-Based Learning
        # ==========================================
        if DEEPSEEK_KEY and ENABLE_DEEPSEEK:
            try:
                from openai import AsyncOpenAI
                self.deepseek_client = AsyncOpenAI(
                    api_key=DEEPSEEK_KEY,
                    base_url=DEEPSEEK_BASE_URL,
                    timeout=self.timeout
                )
                print("[LLM] ✅ DeepSeek initialized (Place-Based Learning Specialist)")
            except ImportError:
                print("[LLM] ❌ WARNING: openai package not installed for DeepSeek")
                self.deepseek_client = None
            except Exception as e:
                print(f"[LLM] ❌ Failed to initialize DeepSeek: {e}")
                self.deepseek_client = None
        else:
            self.deepseek_client = None
            if not DEEPSEEK_KEY:
                print("[LLM] ⚠️  DeepSeek not configured (no DEEPSEEK_API_KEY)")
            elif not ENABLE_DEEPSEEK:
                print("[LLM] ⚠️  DeepSeek disabled (ENABLE_DEEPSEEK=false)")

    async def call(self, provider: str, prompt: str, **kwargs) -> str:
        """
        Call the specified LLM and return the response text.
        
        Args:
            provider: "chatgpt" | "claude" | "deepseek"
            prompt: user input text
            **kwargs: additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            str: LLM response text
        """
        provider = provider.lower()
        
        # Mock mode for testing
        if API_MODE == "mock":
            return await self._mock_response(provider, prompt)
        
        # Real API calls with retry logic
        for attempt in range(self.max_retries):
            try:
                if provider == "chatgpt":
                    return await self._call_chatgpt(prompt, **kwargs)
                elif provider == "claude":
                    return await self._call_claude(prompt, **kwargs)
                elif provider == "deepseek":
                    return await self._call_deepseek(prompt, **kwargs)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"[LLM] Retry {attempt + 1}/{self.max_retries} after {wait_time}s for {provider}: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[LLM] ERROR: All retries failed for {provider}: {str(e)}")
                    raise

    async def _call_chatgpt(self, prompt: str, **kwargs) -> str:
        """Call ChatGPT API (GPT-4o)"""
        if not self.openai_client:
            raise ValueError("GPT client not initialized")
        
        response = await self.openai_client.chat.completions.create(
            model=kwargs.get('model', OPENAI_MODEL),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 4000),
            timeout=self.timeout
        )
        return response.choices[0].message.content

    async def _call_claude(self, prompt: str, **kwargs) -> str:
        """Call Claude API (Sonnet 4) with enhanced formatting control for narrative output"""
        if not self.claude_client:
            raise ValueError("Claude client not initialized")
        
        # ✅ System prompt - 定义 Claude 的角色和输出规则
        system_prompt = """You are an expert educator in Aotearoa New Zealand writing professional lesson plans.

    CRITICAL OUTPUT RULES:
    1. Write in flowing narrative paragraphs (like an article or professional document)
    2. NEVER use numbered sections like 1.1, 1.2, 2.1, 2.2
    3. NEVER use Python list syntax like ['item1', 'item2']
    4. NEVER output JSON, dictionary, or code-like formats
    5. Use markdown headings (##) but all content must be natural paragraphs

    Example of CORRECT format:
    **Overview:**
    This lesson for upper primary students explores cultural concepts through hands-on activities. Students begin by discussing their prior knowledge...

    Example of WRONG format (NEVER DO THIS):
    1.1 Knowledge: ['concept1', 'concept2']
    **Assessment**
    7.1 Formative: ...

    Your output must read naturally, as if written by a human teacher for other teachers."""
        
        # ✅ 对教案生成请求强化格式要求
        if "IMPROVED LESSON PLAN" in prompt or "improve" in prompt.lower() and "lesson" in prompt.lower():
            enhanced_prompt = f"""<<FORMAT INSTRUCTION>>
    You MUST write this lesson plan in flowing narrative paragraphs.
    Before starting, internally confirm: "I will write naturally in paragraphs, not numbered lists."

    {prompt}

    <<VERIFICATION>>
    After writing, check: Does your output contain "1.1" or "['..." ? If yes, REWRITE in narrative form."""
        else:
            enhanced_prompt = prompt
        
        # ✅ 调用 Claude API
        message = await self.claude_client.messages.create(
            model=kwargs.get('model', ANTHROPIC_MODEL),
            max_tokens=kwargs.get('max_tokens', 4000),
            temperature=kwargs.get('temperature', 0.8),  # 增加创造性，避免模板化
            system=system_prompt,
            messages=[{"role": "user", "content": enhanced_prompt}]
        )
        
        response_text = message.content[0].text
        
        # ✅ 后处理验证和日志
        if "1.1" in response_text or "1.2" in response_text or "['Understanding" in response_text:
            print("[LLM] ⚠️  WARNING: Claude output still contains structured format!")
            print(f"[LLM] First 500 chars: {response_text[:500]}")
            print("[LLM] This may require additional prompt engineering or post-processing")
        else:
            print("[LLM] ✅ Claude output appears to be in narrative format")
        
        return response_text
        
        return message.content[0].text

    async def _call_deepseek(self, prompt: str, **kwargs) -> str:
        """Call DeepSeek API"""
        if not self.deepseek_client:
            raise ValueError("DeepSeek client not initialized")
        
        response = await self.deepseek_client.chat.completions.create(
            model=kwargs.get('model', DEEPSEEK_MODEL),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 4000),
            timeout=self.timeout
        )
        return response.choices[0].message.content

    async def _mock_response(self, provider: str, prompt: str) -> str:
        """Generate mock responses for testing - Framework v3.0"""
        await asyncio.sleep(0.5)  # Simulate network delay
        
        if "place-based" in prompt.lower() or "place based" in prompt.lower():
            return json.dumps({
                "score": 72,
                "strengths": ["Uses local examples", "Connects to community"],
                "areas_for_improvement": ["Specify local landmarks", "Add iwi partnerships"],
                "recommendations": ["Name specific local places", "Partner with local organizations"]
            })
        elif "cultural" in prompt.lower() and "integrated" in prompt.lower():
            # ✅ v3.0: Integrated cultural response
            return json.dumps({
                "score": 68,
                "strengths": ["Acknowledges cultural context", "Includes some Te Reo"],
                "areas_for_improvement": ["Limited mātauranga Māori depth", "More Te Reo needed"],
                "gaps": ["Māori knowledge not central", "Limited iwi consultation"],
                "cultural_elements_present": ["Tikanga references", "Basic Te Reo"],
                "recommendations": ["Consult with local iwi", "Embed mātauranga Māori more deeply"]
            })
        elif "critical pedagogy" in prompt.lower():
            return json.dumps({
                "score": 75,
                "strengths": ["Some critical questions", "Discussion opportunities"],
                "areas_for_improvement": ["Limited student agency", "Could be more dialogic"],
                "recommendations": ["Increase student choice", "Add critical reflection"]
            })
        elif "lesson design" in prompt.lower() or "design quality" in prompt.lower():
            # ✅ v3.0: New lesson design mock
            return json.dumps({
                "score": 78,
                "strengths": ["Clear objectives", "Logical structure"],
                "areas_for_improvement": ["Assessment criteria unclear", "Limited differentiation"],
                "recommendations": ["Add explicit rubrics", "Include differentiation strategies"]
            })
        elif "improve" in prompt.lower() or "generate" in prompt.lower():
            return json.dumps({
                "knowledge": "Comprehensive understanding of key concepts",
                "skills": "Critical analysis and practical skills",
                "values": "Cultural diversity and Indigenous perspectives",
                "materials": "Handouts, digital resources",
                "tech_tools": "Interactive whiteboard, tablets"
            })
        else:
            return json.dumps({
                "score": 70,
                "recommendations": ["General improvement suggestion"]
            })

    def is_available(self, provider: str) -> bool:
        """Check if specific LLM is available"""
        provider = provider.lower()
        if provider == "chatgpt":
            return self.openai_client is not None
        elif provider == "claude":
            return self.claude_client is not None
        elif provider == "deepseek":
            return self.deepseek_client is not None
        return False

    def get_available_llms(self) -> list:
        """Get list of all available LLMs"""
        available = []
        if self.openai_client:
            available.append('chatgpt')
        if self.claude_client:
            available.append('claude')
        if self.deepseek_client:
            available.append('deepseek')
        return available


# Global instance
llm_client = LLMClient()