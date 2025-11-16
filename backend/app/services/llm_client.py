
"""
LLM Client with role assignments:
- Claude: Cultural Responsiveness Evaluator (Indigenous Education Expert)
- DeepSeek: Place-Based Learning Evaluator (Community Resources Integration)
- GPT-4: Critical Pedagogy, Assessment Quality & Reflective Practice Evaluator
"""
import asyncio
import json
from typing import Optional
from app.config import (
    API_MODE, OPENAI_KEY, ANTHROPIC_KEY, DEEPSEEK_KEY,
    OPENAI_MODEL, ANTHROPIC_MODEL, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL,
    API_TIMEOUT, MAX_RETRIES
)


class LLMClient:
    """Unified LLM Client for Multi-Model Support"""
    
    def __init__(self):
        self.timeout = API_TIMEOUT
        self.max_retries = MAX_RETRIES
        self._init_clients()
    
    def _init_clients(self):
        """Initialize all LLM clients with error handling"""
        # Initialize ChatGPT (GPT-4) - Critical Pedagogy & Assessment Evaluator
        if OPENAI_KEY:  # ✅ 移除硬编码的密钥检查
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=OPENAI_KEY, timeout=self.timeout)
                print("[LLM] ✅ ChatGPT initialized (Critical Pedagogy & Assessment Evaluator)")
            except ImportError:
                print("[LLM] ❌ WARNING: openai package not installed")
                self.openai_client = None
            except Exception as e:
                print(f"[LLM] ❌ Failed to initialize ChatGPT: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            print("[LLM] ⚠️ ChatGPT not configured (no OPENAI_API_KEY)")
        
        # Initialize Claude - Cultural Responsiveness Evaluator
        if ANTHROPIC_KEY:  # ✅ 移除硬编码的密钥检查
            try:
                from anthropic import AsyncAnthropic
                self.claude_client = AsyncAnthropic(api_key=ANTHROPIC_KEY, timeout=self.timeout)
                print("[LLM] ✅ Claude initialized (Cultural Responsiveness Evaluator)")
            except ImportError:
                print("[LLM] ❌ WARNING: anthropic package not installed")
                self.claude_client = None
            except Exception as e:
                print(f"[LLM] ❌ Failed to initialize Claude: {e}")
                self.claude_client = None
        else:
            self.claude_client = None
            print("[LLM] ⚠️ Claude not configured (no ANTHROPIC_API_KEY)")
        
        # Initialize DeepSeek - Place-Based Learning Evaluator
        if DEEPSEEK_KEY:  # ✅ 移除硬编码的密钥检查
            try:
                from openai import AsyncOpenAI
                self.deepseek_client = AsyncOpenAI(
                    api_key=DEEPSEEK_KEY,
                    base_url=DEEPSEEK_BASE_URL,
                    timeout=self.timeout
                )
                print("[LLM] ✅ DeepSeek initialized (Place-Based Learning Evaluator)")
            except ImportError:
                print("[LLM] ❌ WARNING: openai package not installed for DeepSeek")
                self.deepseek_client = None
            except Exception as e:
                print(f"[LLM] ❌ Failed to initialize DeepSeek: {e}")
                self.deepseek_client = None
        else:
            self.deepseek_client = None
            print("[LLM] ⚠️ DeepSeek not configured (no DEEPSEEK_API_KEY)")

    async def call(self, provider: str, prompt: str, **kwargs) -> str:
        """
        Call the specified LLM and return the response text.
        provider: "chatgpt" | "claude" | "deepseek"
        prompt: user input text
        **kwargs: additional parameters (temperature, max_tokens, etc.)
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
        """Call ChatGPT API"""
        if not self.openai_client:
            raise ValueError("ChatGPT client not initialized")
        
        response = await self.openai_client.chat.completions.create(
            model=kwargs.get('model', OPENAI_MODEL),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 4000),
            timeout=self.timeout
        )
        return response.choices[0].message.content

    async def _call_claude(self, prompt: str, **kwargs) -> str:
        """Call Claude API - FIXED VERSION"""
        if not self.claude_client:
            raise ValueError("Claude client not initialized")
        
        # Create message using AsyncAnthropic client
        message = await self.claude_client.messages.create(
            model=kwargs.get('model', ANTHROPIC_MODEL),
            max_tokens=kwargs.get('max_tokens', 4000),
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract text from response
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
        """Generate mock responses for testing"""
        await asyncio.sleep(0.5)  # Simulate network delay
        
        if "Place-Based" in prompt or "place-based" in prompt.lower():
            return json.dumps({
                "score": 85,
                "strengths": ["Strong local community connections", "Effective use of local resources"],
                "weaknesses": ["Limited field trip opportunities"],
                "recommendations": ["Add more local case studies", "Include community partnerships"]
            })
        elif "Cultural" in prompt or "cultural" in prompt.lower():
            return json.dumps({
                "score": 78,
                "strengths": ["Acknowledges Maori perspectives"],
                "weaknesses": ["Limited te reo Maori usage"],
                "recommendations": ["Incorporate more te reo Maori", "Add cultural protocols"]
            })
        elif "Critical Pedagogy" in prompt or "critical" in prompt.lower():
            return json.dumps({
                "score": 82,
                "strengths": ["Encourages critical questioning"],
                "weaknesses": ["Could promote more student voice"],
                "recommendations": ["Add critical thinking activities", "Include social justice themes"]
            })
        elif "Assessment" in prompt or "assessment" in prompt.lower():
            return json.dumps({
                "score": 80,
                "strengths": ["Clear success criteria"],
                "weaknesses": ["Limited formative assessment"],
                "recommendations": ["Add more ongoing assessments", "Include peer feedback"]
            })
        elif "Reflective" in prompt or "reflective" in prompt.lower():
            return json.dumps({
                "score": 76,
                "strengths": ["Some reflection activities"],
                "weaknesses": ["Could be more structured"],
                "recommendations": ["Add reflection journals", "Include metacognitive prompts"]
            })
        elif "improve" in prompt.lower() or "generator" in prompt.lower() or "generate" in prompt.lower():
            return json.dumps({
                "knowledge": "Students will develop comprehensive understanding of key concepts.",
                "skills": "Students will develop critical analysis and practical skills.",
                "values": "Students will appreciate cultural diversity and Indigenous perspectives.",
                "prior_knowledge": "Students bring varied experiences from previous lessons.",
                "interests": "Topics connect to students' everyday experiences.",
                "challenges": "Varying literacy levels and learning paces.",
                "learning_styles": "Visual, auditory, and kinesthetic learners.",
                "accommodations": "Differentiated materials and support.",
                "key_concepts": "Core curriculum concepts with local context.",
                "focus_challenges": "Abstract concepts requiring scaffolding.",
                "methods": "Place-based learning and collaborative inquiry.",
                "strategies": "Think-pair-share, jigsaw, project-based learning.",
                "teacher_prep": "Review materials, prepare resources.",
                "student_prep": "Prior reading, gather materials.",
                "intro_duration": "20",
                "intro_tasks": "Activate prior knowledge.",
                "intro_teacher_actions": "Facilitate discussion, present objectives.",
                "intro_student_activities": "Share ideas, ask questions.",
                "main_duration": "40",
                "main_tasks": "Explore key concepts.",
                "main_teacher_actions": "Teach, model, check understanding.",
                "main_student_activities": "Take notes, practice skills.",
                "investigation_duration": "45",
                "investigation_tasks": "Hands-on investigation.",
                "investigation_teacher_actions": "Guide inquiry, facilitate groups.",
                "investigation_student_activities": "Investigate, collaborate, analyze.",
                "conclusion_duration": "15",
                "conclusion_tasks": "Synthesize learning.",
                "conclusion_teacher_actions": "Summarize, facilitate reflection.",
                "conclusion_student_activities": "Share insights, reflect.",
                "extension_duration": "Ongoing",
                "extension_tasks": "Extend beyond classroom.",
                "extension_teacher_actions": "Provide resources, support projects.",
                "extension_student_activities": "Independent research.",
                "formative": "Observation, questioning, exit tickets.",
                "summative": "Project, written assessment.",
                "feedback": "Regular feedback during activities.",
                "materials": "Handouts, manipulatives, digital resources.",
                "tech_tools": "Interactive whiteboard, tablets."
            })
        else:
            return json.dumps({
                "score": 75,
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