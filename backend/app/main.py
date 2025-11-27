from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import Database, init_database
from typing import List, Optional
from pydantic import BaseModel
import traceback
from contextlib import asynccontextmanager
from io import BytesIO
import json
import time
import asyncio
from functools import wraps

import logging
import re

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("uvicorn")

# 性能监控装饰器
def timing_decorator(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            print(f"⏱️ {func.__name__} executed in {end_time - start_time:.2f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            print(f"⏱️ {func.__name__} failed after {end_time - start_time:.2f} seconds: {e}")
            raise
    return wrapper

# 分数进度条颜色辅助函数
def score_color(score: Optional[int]) -> str:
    if score is None:
        return "grey"
    try:
        return "red" if score < 60 else "orange" if score < 80 else "green"
    except Exception:
        return "grey"

# 文件处理库
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx not installed")

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PyPDF2 not installed")

from app.config import API_MODE
from app.services.llm_client import LLMClient

# 导入理论框架加载器
from app.services.framework_loader import get_framework_loader

# 导入评估辅助函数
from app.utils.evaluation_helpers import (
    extract_score_from_response,
    extract_recommendations_from_response,
    extract_strengths_from_response,  
    extract_areas_for_improvement_from_response, 
    parse_json_response,
    calculate_weighted_score,
    merge_and_deduplicate_recommendations
)

# ✅ 导入 API 控制配置
from app.config import (
    ENABLE_DEEPSEEK, 
    ENABLE_CLAUDE, 
    ENABLE_GPT,
    API_TIMEOUT,
    API_MAX_RETRIES,
    API_RETRY_DELAY
)

# 初始化框架加载器
framework_loader = get_framework_loader()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    try:
        print("🚀 Starting application...")
        
        # 数据库初始化
        init_database(reset=False)
        print("✅ Database initialized successfully")
        
        # 框架会在第一次使用时自动加载
        print("ℹ️  Framework will be loaded on first use")
        
    except Exception as e:
        print(f"⚠️ Initialization warning: {e}")
        import traceback
        traceback.print_exc()
    
    yield  # 应用开始接受请求
    
    print("👋 Application shutdown")

app = FastAPI(title="Lesson Plan Evaluator API v3.0", lifespan=lifespan)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# -------- Models --------
class EvaluationCreate(BaseModel):
    lesson_plan_text: str
    lesson_plan_title: Optional[str] = None
    grade_level: Optional[str] = None
    subject_area: Optional[str] = None

class EvaluationUpdate(BaseModel):
    place_based_score: Optional[int] = None
    cultural_score: Optional[int] = None
    overall_score: Optional[int] = None
    status: Optional[str] = None
    agent_responses: Optional[List[dict]] = None
    debate_transcript: Optional[dict] = None
    recommendations: Optional[List[str]] = None

class ImproveLessonRequest(BaseModel):
    original_lesson: str
    lesson_title: str
    grade_level: Optional[str] = None
    subject_area: Optional[str] = None
    recommendations: List[str]
    scores: dict
    remove_numbering: Optional[bool] = False

def get_db():
    db = Database()
    db.connect()
    try:
        yield db
    finally:
        db.close()

# -------- 文件处理函数 --------
def extract_text_from_docx(file_bytes: bytes) -> str:
    """从DOCX文件提取文本"""
    if not DOCX_AVAILABLE:
        raise HTTPException(status_code=501, detail="DOCX support not available")
    
    try:
        doc = docx.Document(BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read DOCX: {str(e)}")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """从PDF文件提取文本"""
    if not PDF_AVAILABLE:
        raise HTTPException(status_code=501, detail="PDF support not available")
    
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")

# -------- Lesson Plan Template --------
LESSON_PLAN_TEMPLATE = """
**1. Learning Objectives**
1.1 Knowledge: {knowledge}
1.2 Skills: {skills}
1.3 Attitudes/Values: {values}

**2. Learner Analysis**
2.1 Student Background:
2.1.1 Prior knowledge or skills related to the topic: {prior_knowledge}
2.1.2 Possible interests or connections to the topic: {interests}
2.1.3 Anticipated challenges or difficulties: {challenges}
2.2 Learner Characteristics:
2.2.1 Learning styles: {learning_styles}
2.2.2 Special needs or accommodations: {accommodations}

**3. Key Points of Focus**
3.1 Teaching Focus (Key Concepts): {key_concepts}
3.2 Challenges (Potential Difficulties): {focus_challenges}

**4. Teaching Methods and Strategies**
4.1 Methods: {methods}
4.2 Strategies: {strategies}

**5. Preparation**
5.1 Teacher Preparation: {teacher_prep}
5.2 Student Preparation: {student_prep}

**6. Lesson Procedure**

6.1 Introduction ({intro_duration}mins)：
- Key Tasks: {intro_tasks}
- Teacher Actions: {intro_teacher_actions}
- Student Activities: {intro_student_activities}

6.2 Main Teaching ({main_duration}mins)：
- Key Tasks: {main_tasks}
- Teacher Actions: {main_teacher_actions}
- Student Activities: {main_student_activities}

6.3 Investigation & Exploration ({investigation_duration}mins):
- Key Tasks: {investigation_tasks}
- Teacher Actions: {investigation_teacher_actions}
- Student Activities: {investigation_student_activities}

6.4 Conclusion ({conclusion_duration}mins):
- Key Tasks: {conclusion_tasks}
- Teacher Actions: {conclusion_teacher_actions}
- Student Activities: {conclusion_student_activities}

6.5 Extension ({extension_duration}mins):
- Key Tasks: {extension_tasks}
- Teacher Actions: {extension_teacher_actions}
- Student Activities: {extension_student_activities}

**7. Assessment**
7.1 Formative Assessment: {formative}
7.2 Summative Assessment: {summative}
7.3 Feedback Mechanisms: {feedback}

**8. Resources and Tools**
8.1 Materials Needed: {materials}
8.2 Technology and Tools: {tech_tools}

**Cultural Disclaimers and Acknowledgment of Limitations:**
This AI-generated lesson plan requires your review and adaptation before use. Please consult with local iwi and cultural advisors for Māori content. AI systems lack cultural understanding and lived experience—critically evaluate all content for cultural appropriateness and te reo Māori accuracy. You retain full responsibility for ensuring this lesson suits your teaching context and respects local protocols.
"""

def generate_lesson_plan_from_fields(fields: dict) -> str:
    """根据字段生成教案"""
    try:
        return LESSON_PLAN_TEMPLATE.format(**fields)
    except KeyError as e:
        print(f"⚠️ Missing field in template: {e}")
        default_fields = {
            "knowledge": "Students will develop comprehensive understanding.",
            "skills": "Students will develop critical thinking skills.",
            "values": "Students will appreciate diverse perspectives.",
            "prior_knowledge": "Students bring varied experiences.",
            "interests": "Connecting to student interests.",
            "challenges": "Addressing diverse learning needs.",
            "learning_styles": "Accommodating diverse learning preferences.",
            "accommodations": "Providing appropriate supports.",
            "key_concepts": "Core concepts aligned with curriculum.",
            "focus_challenges": "Key learning challenges to address.",
            "methods": "Place-based and inquiry-based learning.",
            "strategies": "Evidence-based instructional strategies.",
            "teacher_prep": "Required teacher preparations.",
            "student_prep": "Student preparations.",
            "intro_duration": "20",
            "intro_tasks": "Activate prior knowledge.",
            "intro_teacher_actions": "Facilitate discussion.",
            "intro_student_activities": "Share prior knowledge.",
            "main_duration": "40",
            "main_tasks": "Introduce core concepts.",
            "main_teacher_actions": "Present content with scaffolding.",
            "main_student_activities": "Take notes and practice.",
            "investigation_duration": "45",
            "investigation_tasks": "Apply learning through investigation.",
            "investigation_teacher_actions": "Facilitate group work.",
            "investigation_student_activities": "Conduct investigations.",
            "conclusion_duration": "15",
            "conclusion_tasks": "Synthesize learning.",
            "conclusion_teacher_actions": "Guide reflection.",
            "conclusion_student_activities": "Share insights.",
            "extension_duration": "Ongoing",
            "extension_tasks": "Extend learning beyond classroom.",
            "extension_teacher_actions": "Provide additional resources.",
            "extension_student_activities": "Complete independent research.",
            "formative": "Ongoing observation and feedback.",
            "summative": "Final assessment of learning outcomes.",
            "feedback": "Regular constructive feedback.",
            "materials": "Required teaching materials.",
            "tech_tools": "Technology tools and resources."
        }
        merged_fields = {**default_fields, **fields}
        return LESSON_PLAN_TEMPLATE.format(**merged_fields)
    
# 添加验证函数
def validate_lesson_format(lesson_text: str) -> dict:
    """
    验证教案格式质量
    检测是否包含结构化格式、Python 列表语法等问题
    
    Returns:
        dict: {
            "valid": bool,
            "issues": List[str],
            "char_count": int,
            "has_te_reo": bool,
            "has_specific_places": bool
        }
    """
    issues = []
    warnings = []
    
    # ❌ 检测结构化格式
    if "1.1" in lesson_text or "1.2" in lesson_text or "2.1" in lesson_text:
        issues.append("Contains numbered sections (1.1, 1.2, 2.1, etc.)")
    
    # ❌ 检测 Python 列表语法
    if "['Understanding" in lesson_text or '["Understanding' in lesson_text:
        issues.append("Contains Python list syntax")
    
    # ❌ 检测 JSON 格式
    if lesson_text.strip().startswith('{') and '"knowledge":' in lesson_text:
        issues.append("Appears to be JSON format instead of narrative")
    
    # ⚠️ 检测长度
    if len(lesson_text) < 1000:
        issues.append("Too short (less than 1000 chars)")
    elif len(lesson_text) < 1500:
        warnings.append("Relatively short (less than 1500 chars)")
    
    # ✅ 检测 Te Reo 内容
    has_te_reo = any(term in lesson_text for term in [
        'Te Reo', 'Māori', 'Kia ora', 'whānau', 'mana', 
        'kaitiakitanga', 'whanaungatanga', 'whakapapa'
    ])
    if not has_te_reo:
        warnings.append("No Te Reo Māori terms detected")
    
    # ✅ 检测具体地点
    has_specific_places = any(place in lesson_text for place in [
        'Auckland', 'Wellington', 'Canterbury', 'Ōrākei', 'Te Papa',
        'Museum', 'Marae', 'Waitangi'
    ])
    if not has_specific_places:
        warnings.append("No specific local places named")
    
    # ✅ 检测批判性问题
    has_critical_questions = any(q in lesson_text.lower() for q in [
        'whose stories', 'whose voices', 'different perspectives',
        'why might different', 'how has'
    ])
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "char_count": len(lesson_text),
        "word_count": len(lesson_text.split()),
        "has_te_reo": has_te_reo,
        "has_specific_places": has_specific_places,
        "has_critical_questions": has_critical_questions
    }

    # -------- 辅助函数：构建 analysis 结构 --------
def build_analysis_structure(
    dimension_key,
    score,
    response_text,
    recommendations=None,
    strengths=None,
    areas_for_improvement=None,
    gaps=None,
    cultural_elements=None
):
    """
    构建前端期望的 analysis 结构 - Framework v3.0
    
    ✅ 重要区别:
    - strengths: 优点/做得好的地方
    - areas_for_improvement: 需要改进的领域/缺陷 (问题陈述)
    - recommendations: 具体的改进建议 (解决方案)
    """
    return {
        dimension_key: {
            "score": score,
            "response_text": response_text or "",
            "strengths": strengths or [],
            "areas_for_improvement": areas_for_improvement or [],
            "gaps": gaps or [],
            "recommendations": recommendations or [],
            "cultural_elements_present": cultural_elements or [],
            "summary": (response_text[:500] if response_text else "")
        }
    }


# -------- API 端点 --------

@app.get("/")
async def root():
    """API根路径 - 显示系统状态和理论框架信息"""
    framework = framework_loader.load_theoretical_framework()
    agent_design = framework_loader.load_agent_design()
    
    return {
        "message": "Lesson Plan Evaluator API with Theoretical Framework v3.0",
        "mode": API_MODE,
        "database": "connected",
        "status": "operational",
        "theoretical_framework": {
            "name": framework.get('framework_metadata', {}).get('name', 'Default'),
            "version": framework.get('framework_metadata', {}).get('version', '3.0'),
            "dimensions": list(framework.get('dimensions', {}).keys()),
            "agents_configured": len(agent_design.get('agents', {}))
        },
        "features": {
            "file_upload": {
                "word": DOCX_AVAILABLE,
                "pdf": PDF_AVAILABLE
            }
        },
        "api_status": {
            "deepseek": "enabled" if ENABLE_DEEPSEEK else "disabled",
            "claude": "enabled" if ENABLE_CLAUDE else "disabled",
            "gpt": "enabled" if ENABLE_GPT else "disabled"
        }
    }


@app.get("/api/framework")
async def get_framework_info():
    """获取理论框架的详细信息"""
    framework = framework_loader.load_theoretical_framework()
    agent_design = framework_loader.load_agent_design()
    weights = framework_loader.get_scoring_weights()
    
    dimensions_summary = {}
    for dim_code, dim_info in framework.get('dimensions', {}).items():
        dimensions_summary[dim_code] = {
            "label": dim_info.get('label', ''),
            "definition": dim_info.get('definition', ''),
            "indicator_count": len(dim_info.get('indicators', [])),
            "weight": weights.get(dim_code, 0.0)
        }
    
    agents_summary = {}
    for agent_id, agent_info in agent_design.get('agents', {}).items():
        agents_summary[agent_info['name']] = {
            "role": agent_info.get('role', ''),
            "dimensions": agent_info.get('assigned_dimensions', [])
        }
    
    return {
        "status": "success",
        "framework_metadata": framework.get('framework_metadata', {}),
        "dimensions": dimensions_summary,
        "agents": agents_summary,
        "composite_scoring": {
            "method": framework.get('composite_scoring', {}).get('method', 'weighted_average'),
            "weights": weights
        }
    }


@app.get("/api/framework/dimension/{dimension_code}")
async def get_dimension_details(dimension_code: str):
    """获取特定维度的详细指标信息"""
    framework = framework_loader.load_theoretical_framework()
    dimensions = framework.get('dimensions', {})
    
    if dimension_code not in dimensions:
        raise HTTPException(
            status_code=404, 
            detail=f"Dimension '{dimension_code}' not found"
        )
    
    dimension_info = dimensions[dimension_code]
    
    indicators = []
    for indicator in dimension_info.get('indicators', []):
        indicators.append({
            "code": indicator.get('code', ''),
            "name": indicator.get('name', ''),
            "definition": indicator.get('definition', ''),
            "source": indicator.get('source', '')
        })
    
    return {
        "status": "success",
        "code": dimension_code,
        "label": dimension_info.get('label', ''),
        "definition": dimension_info.get('definition', ''),
        "theoretical_foundation": dimension_info.get('theoretical_foundation', {}),
        "indicators": indicators,
        "scoring_rubric": dimension_info.get('scoring_rubric', {})
    }


@app.post("/api/upload-file")
async def upload_lesson_plan_file(file: UploadFile = File(...)):
    """上传DOCX或PDF文件并提取文本"""
    try:
        file_bytes = await file.read()
        
        if file.filename.endswith('.docx'):
            text = extract_text_from_docx(file_bytes)
        elif file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(file_bytes)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Use .docx or .pdf"
            )
        
        return {
            "status": "success",
            "filename": file.filename,
            "text": text,
            "length": len(text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"File processing failed: {str(e)}"
        )


@app.post("/api/extract-text")
async def extract_text_from_file(file: UploadFile = File(...)):
    """提取上传文件（PDF、DOCX）中的文本内容"""
    try:
        print(f"\n📄 Processing uploaded file: {file.filename}")
        print(f"📊 Content type: {file.content_type}")
        
        file_bytes = await file.read()
        file_size = len(file_bytes)
        print(f"📏 File size: {file_size} bytes ({file_size/1024:.1f} KB)")
        
        text = ""
        metadata = {}
        
        if file.filename.endswith('.docx') or file.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            if not DOCX_AVAILABLE:
                raise HTTPException(
                    status_code=500,
                    detail="DOCX processing not available. Please install python-docx package."
                )
            
            print("📝 Extracting text from DOCX...")
            text = extract_text_from_docx(file_bytes)
            
            try:
                doc = docx.Document(BytesIO(file_bytes))
                if doc.paragraphs and doc.paragraphs[0].text.strip():
                    first_para = doc.paragraphs[0].text.strip()
                    if len(first_para) < 100 and not first_para.endswith('.'):
                        metadata['title'] = first_para
                
                if hasattr(doc.core_properties, 'title') and doc.core_properties.title:
                    metadata['title'] = doc.core_properties.title
            except Exception as e:
                print(f"⚠️ Could not extract metadata: {e}")
            
        elif file.filename.endswith('.pdf') or file.content_type == 'application/pdf':
            if not PDF_AVAILABLE:
                raise HTTPException(
                    status_code=500,
                    detail="PDF processing not available. Please install PyPDF2 package."
                )
            
            print("📕 Extracting text from PDF...")
            text = extract_text_from_pdf(file_bytes)
            
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF and Word (.docx, .doc) files are supported."
            )
        
        if not text or len(text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Could not extract sufficient text from file. File may be empty or corrupted."
            )
        
        print(f"✅ Successfully extracted {len(text)} characters")
        print(f"📄 Preview: {text[:200]}...")
        
        return {
            "status": "success",
            "filename": file.filename,
            "text": text.strip(),
            "length": len(text),
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ File extraction error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"File processing failed: {str(e)}"
        )


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok", 
        "message": "Service is healthy",
        "framework_loaded": framework_loader._framework is not None,
        "framework_version": "3.0",
        "api_config": {
            "deepseek_enabled": ENABLE_DEEPSEEK,
            "claude_enabled": ENABLE_CLAUDE,
            "gpt_enabled": ENABLE_GPT,
            "timeout": API_TIMEOUT,
            "max_retries": API_MAX_RETRIES,
            "retry_delay": API_RETRY_DELAY
        }
    }

@app.post("/api/evaluate")
@app.post("/api/evaluate/lesson")
@timing_decorator
async def evaluate_lesson_plan(
    request: EvaluationCreate, 
    db: Database = Depends(get_db)
):
    """
    评估教案 - Framework v3.0 
    ✅ 4 个维度：Place-based, Cultural Responsiveness (Integrated), Critical Pedagogy, Lesson Design Quality
    ✅ 4 个 Agents: DeepSeek, Claude, GPT-Critical, GPT-Design
    """
    print(f"\n{'='*60}")
    print(f"📝 New Evaluation Request (Framework v3.0)")
    print(f"{'='*60}")
    
    text = request.lesson_plan_text.strip()
    title = request.lesson_plan_title or "Untitled Lesson Plan"
    grade_level = request.grade_level
    subject_area = request.subject_area
    
    if not text:
        raise HTTPException(status_code=400, detail="Lesson plan text cannot be empty")
    
    print(f"📄 Title: {title}")
    print(f"📊 Grade: {grade_level}, Subject: {subject_area}")
    print(f"📏 Length: {len(text)} characters")
    
    llm_client = LLMClient()
    
    print("\n🔧 Loading framework v3.0 prompts...")
    deepseek_prompt_template = framework_loader.load_prompt('deepseek')
    claude_prompt_template = framework_loader.load_prompt('claude')
    gpt_critical_prompt_template = framework_loader.load_prompt('gpt_critical')
    gpt_design_prompt_template = framework_loader.load_prompt('gpt_design')
    
    agent_responses = []
    place_based_score = 0
    cultural_score = 0
    critical_pedagogy_score = 0
    lesson_design_score = 0
    overall_score = 0
    lesson_plan_text = ""
    recommendations = []
    eval_id = None
    
    if API_MODE == "real":
        print("\n🤖 Using REAL API mode with framework v3.0 prompts")
        print(f"   Active APIs: DeepSeek={ENABLE_DEEPSEEK}, Claude={ENABLE_CLAUDE}, GPT={ENABLE_GPT}")
        print(f"   Config: Timeout={API_TIMEOUT}s, Retries={API_MAX_RETRIES}, Delay={API_RETRY_DELAY}s")
        print("="*60)
        
        try:
            # ==========================================
            # AGENT 1: DeepSeek - Place-based Learning (PBL)
            # ==========================================
            if ENABLE_DEEPSEEK:
                print("\n🔵 Agent 1: DeepSeek (Place-based Learning Specialist)")
                print("-" * 60)
                
                deepseek_full_prompt = deepseek_prompt_template.replace("{lesson_plan_text}", text)
                print(f"📝 Using framework prompt ({len(deepseek_full_prompt)} chars)")
                
                deepseek_start = time.time()
                deepseek_success = False
                
                for retry in range(API_MAX_RETRIES):
                    try:
                        print(f"🔄 DeepSeek attempt {retry+1}/{API_MAX_RETRIES}...")
                        deepseek_response = await asyncio.wait_for(
                            llm_client.call("deepseek", deepseek_full_prompt),
                            timeout=API_TIMEOUT
                        )
                        deepseek_time = time.time() - deepseek_start
                        print(f"✅ DeepSeek responded in {deepseek_time:.2f}s")
                        
                        place_based_score = extract_score_from_response(deepseek_response, "place_based")
                        print(f"📊 Extracted score: {place_based_score}/100")
                        
                        ds_recs = extract_recommendations_from_response(deepseek_response) or []
                        print(f"📋 Extracted {len(ds_recs)} recommendations")
                        
                        agent_responses.append({
                            "agent": "DeepSeek",
                            "model": "deepseek-chat",
                            "role": "Place-based Learning Specialist",
                            "dimension": "place_based_learning",
                            "response": deepseek_response,
                            "analysis": build_analysis_structure(
                                "place_based_learning", 
                                place_based_score, 
                                deepseek_response,
                                recommendations=ds_recs
                            ),
                            "recommendations": ds_recs,
                            "score": place_based_score,
                            "time": deepseek_time
                        })
                        deepseek_success = True
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"❌ DeepSeek attempt {retry+1}/{API_MAX_RETRIES} failed: {error_msg}")
                        
                        if "403" in error_msg or "401" in error_msg or "insufficient" in error_msg.lower():
                            print("🔑 Authentication/credit issue - stopping retries")
                            break
                        
                        if retry < API_MAX_RETRIES - 1:
                            print(f"⏳ Waiting {API_RETRY_DELAY}s before retry...")
                            await asyncio.sleep(API_RETRY_DELAY)
                
                if not deepseek_success:
                    print("⚠️ DeepSeek: All attempts failed, using zero score")
                    place_based_score = 0
                    agent_responses.append({
                        "agent": "DeepSeek",
                        "model": "deepseek-chat",
                        "role": "Place-based Learning Specialist",
                        "dimension": "place_based_learning",
                        "response": "Service unavailable after retries",
                        "analysis": build_analysis_structure("place_based_learning", 0, "Service unavailable"),
                        "recommendations": [],
                        "score": 0,
                        "time": 0
                    })
            else:
                print("\n🔵 Agent 1: DeepSeek - ⚠️ DISABLED")
                place_based_score = 0
            
            # ==========================================
            # AGENT 2: Claude - Cultural Responsiveness & Māori Perspectives (INTEGRATED)
            # ✅ Framework v3.0: 完全整合的文化维度
            # ==========================================
            if ENABLE_CLAUDE:
                print("\n🟣 Agent 2: Claude (Cultural Responsiveness & Māori Perspectives - Integrated)")
                print("-" * 60)
                
                # ✅ 临时调试：检查函数是否可用
                print(f"DEBUG: extract_strengths_from_response available: {callable(extract_strengths_from_response)}")
                print(f"DEBUG: extract_areas_for_improvement_from_response available: {callable(extract_areas_for_improvement_from_response)}")


                claude_full_prompt = claude_prompt_template.replace("{lesson_plan_text}", text)
                print(f"📝 Using framework v3.0 integrated prompt ({len(claude_full_prompt)} chars)")
                
                claude_start = time.time()
                claude_success = False
                
                for retry in range(API_MAX_RETRIES):
                    try:
                        print(f"🔄 Claude attempt {retry+1}/{API_MAX_RETRIES}...")
                        claude_response = await asyncio.wait_for(
                            llm_client.call("claude", claude_full_prompt),
                            timeout=API_TIMEOUT
                        )
                        claude_time = time.time() - claude_start
                        print(f"✅ Claude responded in {claude_time:.2f}s")
                        
                        # ✅ 临时调试：打印 Claude 原始响应的前 3000 字符
                        print(f"\n{'='*60}")
                        print("Claude Raw Response (first 3000 chars):")
                        print(claude_response[:3000])
                        print(f"{'='*60}\n")
                        
                        # ✅ v3.0: 只提取一个分数 (cultural_responsiveness_integrated)
                        cultural_score = extract_score_from_response(claude_response, "cultural")
                        print(f"📊 Cultural Responsiveness (Māori contexts) score: {cultural_score}/100")
                        
                        # ✅ 提取 Strengths
                        claude_strengths = extract_strengths_from_response(claude_response) or []
                        print(f"✅ Extracted {len(claude_strengths)} strengths")

                        # ✅ 提取 Areas for Improvement
                        claude_areas = extract_areas_for_improvement_from_response(claude_response) or []
                        print(f"🔧 Extracted {len(claude_areas)} areas for improvement")

                        # ✅ 提取 Recommendations
                        claude_recs = extract_recommendations_from_response(claude_response) or []
                        print(f"📋 Extracted {len(claude_recs)} recommendations")
                        
                        # ✅ v3.0: 只构建一个维度的 analysis, 使用分开的数据
                        agent_responses.append({
                            "agent": "Claude",
                            "model": "claude-sonnet-4-20250514",
                            "role": "Cultural Responsiveness & Māori Perspectives Specialist (Integrated)",
                            "dimension": "cultural_responsiveness_integrated",  # ✅ v3.0 key
                            "response": claude_response,
                            "analysis": build_analysis_structure(
                                "cultural_responsiveness_integrated",
                                cultural_score,
                                claude_response,
                                recommendations=claude_recs,
                                strengths=claude_strengths,
                                areas_for_improvement=claude_areas
                            ),
                            "recommendations": claude_recs,
                            "score": cultural_score,
                            "time": claude_time
                        })
                        claude_success = True
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"❌ Claude attempt {retry+1}/{API_MAX_RETRIES} failed: {error_msg}")
                        
                        if "529" in error_msg or "overload" in error_msg.lower():
                            wait_time = API_RETRY_DELAY * (retry + 1)
                            print(f"⏳ Server overloaded. Waiting {wait_time}s before retry...")
                            await asyncio.sleep(wait_time)
                        elif retry < API_MAX_RETRIES - 1:
                            print(f"⏳ Waiting {API_RETRY_DELAY}s before retry...")
                            await asyncio.sleep(API_RETRY_DELAY)
                
                if not claude_success:
                    print("⚠️ Claude: All attempts failed, using zero score")
                    cultural_score = 0
                    agent_responses.append({
                        "agent": "Claude",
                        "model": "claude-sonnet-4-20250514",
                        "role": "Cultural Responsiveness & Māori Perspectives Specialist (Integrated)",
                        "dimension": "cultural_responsiveness_integrated",
                        "response": "Service unavailable after retries",
                        "analysis": build_analysis_structure(
                            "cultural_responsiveness_integrated", 
                            0, 
                            "Service unavailable"
                        ),
                        "recommendations": [],
                        "score": 0,
                        "time": 0
                    })
            else:
                print("\n🟣 Agent 2: Claude - ⚠️ DISABLED")
                cultural_score = 0
            
            # ==========================================
            # AGENT 3: GPT-Critical - Critical Pedagogy (CP)
            # ✅ Framework v3.0: 使用 GPT-Critical 命名
            # ==========================================
            if ENABLE_GPT:
                print("\n🟢 Agent 3: GPT-Critical (Critical Pedagogy Specialist)")
                print("-" * 60)
                
                gpt_critical_full_prompt = gpt_critical_prompt_template.replace("{lesson_plan_text}", text)
                print(f"📝 Using framework v3.0 prompt ({len(gpt_critical_full_prompt)} chars)")
                
                gpt_critical_start = time.time()
                gpt_critical_success = False
                
                for retry in range(API_MAX_RETRIES):
                    try:
                        print(f"🔄 GPT-Critical attempt {retry+1}/{API_MAX_RETRIES}...")
                        gpt_critical_response = await asyncio.wait_for(
                            llm_client.call("chatgpt", gpt_critical_full_prompt),
                            timeout=API_TIMEOUT
                        )
                        gpt_critical_time = time.time() - gpt_critical_start
                        print(f"✅ GPT-Critical responded in {gpt_critical_time:.2f}s")
                        
                        # ✅ 临时调试：打印原始响应
                        print(f"\n{'='*60}")
                        print("GPT-Critical Raw Response (first 2000 chars):")
                        print(gpt_critical_response[:2000])
                        print(f"{'='*60}\n")

                        # 提取分数
                        critical_pedagogy_score = extract_score_from_response(gpt_critical_response, "critical")
                        print(f"📊 Extracted score: {critical_pedagogy_score}/100")

                        # ✅ 提取 Strengths
                        gpt_crit_strengths = extract_strengths_from_response(gpt_critical_response) or []
                        print(f"✅ Extracted {len(gpt_crit_strengths)} strengths")

                        # ✅ 提取 Areas for Improvement
                        gpt_crit_areas = extract_areas_for_improvement_from_response(gpt_critical_response) or []
                        print(f"🔧 Extracted {len(gpt_crit_areas)} areas for improvement")

                        # ✅ 提取 Recommendations
                        gpt_crit_recs = extract_recommendations_from_response(gpt_critical_response) or []
                        print(f"📋 Extracted {len(gpt_crit_recs)} recommendations")
                        
                        agent_responses.append({
                            "agent": "GPT-Critical",  #  v3.0: 区分名称
                            "model": "gpt-4o",
                            "role": "Critical Pedagogy Specialist",
                            "dimension": "critical_pedagogy",
                            "response": gpt_critical_response,
                            "analysis": build_analysis_structure(
                                "critical_pedagogy", 
                                critical_pedagogy_score, 
                                gpt_critical_response,
                                recommendations=gpt_crit_recs,
                                strengths=gpt_crit_strengths,
                                areas_for_improvement=gpt_crit_areas
                            ),
                            "recommendations": gpt_crit_recs,
                            "score": critical_pedagogy_score,
                            "time": gpt_critical_time
                        })
                        gpt_critical_success = True
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"❌ GPT-Critical attempt {retry+1}/{API_MAX_RETRIES} failed: {error_msg}")
                        if retry < API_MAX_RETRIES - 1:
                            print(f"⏳ Waiting {API_RETRY_DELAY}s before retry...")
                            await asyncio.sleep(API_RETRY_DELAY)
                
                if not gpt_critical_success:
                    print("⚠️ GPT-Critical: All attempts failed, using zero score")
                    critical_pedagogy_score = 0
                    agent_responses.append({
                        "agent": "GPT-Critical",
                        "model": "gpt-4o",
                        "role": "Critical Pedagogy Specialist",
                        "dimension": "critical_pedagogy",
                        "response": "Service unavailable after retries",
                        "analysis": build_analysis_structure("critical_pedagogy", 0, "Service unavailable"),
                        "recommendations": [],
                        "score": 0,
                        "time": 0
                    })
            else:
                print("\n🟢 Agent 3: GPT-Critical - ⚠️ DISABLED")
                critical_pedagogy_score = 0
            
            # ==========================================
            # AGENT 4: GPT-Design - Lesson Design Quality (LDQ)
            # ✅ Framework v3.0: 新增维度
            # ==========================================
            if ENABLE_GPT:
                print("\n🟡 Agent 4: GPT-Design (Lesson Design & Quality Specialist)")
                print("-" * 60)
                
                gpt_design_full_prompt = gpt_design_prompt_template.replace("{lesson_plan_text}", text)
                print(f"📝 Using framework v3.0 prompt ({len(gpt_design_full_prompt)} chars)")
                
                gpt_design_start = time.time()
                gpt_design_success = False
                
                for retry in range(API_MAX_RETRIES):
                    try:
                        print(f"🔄 GPT-Design attempt {retry+1}/{API_MAX_RETRIES}...")
                        gpt_design_response = await asyncio.wait_for(
                            llm_client.call("chatgpt", gpt_design_full_prompt),
                            timeout=API_TIMEOUT
                        )
                        gpt_design_time = time.time() - gpt_design_start
                        print(f"✅ GPT-Design responded in {gpt_design_time:.2f}s")
                        
                        # ✅ 临时调试：打印原始响应
                        print(f"\n{'='*60}")
                        print("GPT-Design Raw Response (first 2000 chars):")
                        print(gpt_design_response[:2000])
                        print(f"{'='*60}\n")

                        # 提取分数
                        lesson_design_score = extract_score_from_response(gpt_design_response, "design")
                        print(f"📊 Extracted score: {lesson_design_score}/100")
                        
                        #  提取 Strengths
                        gpt_design_strengths = extract_strengths_from_response(gpt_design_response) or []
                        print(f"✅ Extracted {len(gpt_design_strengths)} strengths")

                        #  提取 Areas for Improvement
                        gpt_design_areas = extract_areas_for_improvement_from_response(gpt_design_response) or []
                        print(f"🔧 Extracted {len(gpt_design_areas)} areas for improvement")

                        #  提取 Recommendations
                        gpt_design_recs = extract_recommendations_from_response(gpt_design_response) or []
                        print(f"📋 Extracted {len(gpt_design_recs)} recommendations")
                        
                        agent_responses.append({
                            "agent": "GPT-Design",  #  v3.0: 区分名称
                            "model": "gpt-4o",
                            "role": "Lesson Design & Quality Specialist",
                            "dimension": "lesson_design_quality",  #  v3.0: 新维度
                            "response": gpt_design_response,
                            "analysis": build_analysis_structure(
                                "lesson_design_quality", 
                                lesson_design_score, 
                                gpt_design_response,
                                recommendations=gpt_design_recs,
                                strengths=gpt_design_strengths,
                                areas_for_improvement=gpt_design_areas
                            ),
                            "recommendations": gpt_design_recs,
                            "score": lesson_design_score,
                            "time": gpt_design_time
                        })
                        gpt_design_success = True
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"❌ GPT-Design attempt {retry+1}/{API_MAX_RETRIES} failed: {error_msg}")
                        if retry < API_MAX_RETRIES - 1:
                            print(f"⏳ Waiting {API_RETRY_DELAY}s before retry...")
                            await asyncio.sleep(API_RETRY_DELAY)
                
                if not gpt_design_success:
                    print("⚠️ GPT-Design: All attempts failed, using zero score")
                    lesson_design_score = 0
                    agent_responses.append({
                        "agent": "GPT-Design",
                        "model": "gpt-4o",
                        "role": "Lesson Design & Quality Specialist",
                        "dimension": "lesson_design_quality",
                        "response": "Service unavailable after retries",
                        "analysis": build_analysis_structure("lesson_design_quality", 0, "Service unavailable"),
                        "recommendations": [],
                        "score": 0,
                        "time": 0
                    })
            else:
                print("\n🟡 Agent 4: GPT-Design - ⚠️ DISABLED")
                lesson_design_score = 0
            
            # ==========================================
            # 计算综合分数（动态权重）
            # ✅ Framework v3.0: 4 个维度，权重 0.25, 0.35, 0.25, 0.15
            # ==========================================
            print("\n📊 Computing composite score (Framework v3.0 dynamic weighting)...")
            
            active_dimensions = {}
            if ENABLE_DEEPSEEK and place_based_score > 0:
                active_dimensions['place_based_learning'] = place_based_score
            if ENABLE_CLAUDE and cultural_score > 0:
                active_dimensions['cultural_responsiveness_integrated'] = cultural_score  # ✅ v3.0 key
            if ENABLE_GPT and critical_pedagogy_score > 0:
                active_dimensions['critical_pedagogy'] = critical_pedagogy_score
            if ENABLE_GPT and lesson_design_score > 0:
                active_dimensions['lesson_design_quality'] = lesson_design_score  # ✅ v3.0 新增

            if active_dimensions:
                original_weights = framework_loader.get_scoring_weights()
                active_weights = {k: original_weights.get(k, 0) for k in active_dimensions.keys()}
                total_weight = sum(active_weights.values())
                
                if total_weight > 0:
                    normalized_weights = {k: v/total_weight for k, v in active_weights.items()}
                    overall_score = calculate_weighted_score(active_dimensions, normalized_weights)
                else:
                    overall_score = sum(active_dimensions.values()) / len(active_dimensions)
                
                print(f"✅ Active dimensions: {list(active_dimensions.keys())}")
                print(f"✅ Composite Score: {overall_score}/100")
                
                for dim, score in active_dimensions.items():
                    weight = normalized_weights.get(dim, 0) if total_weight > 0 else 0
                    print(f"   - {dim}: {score} (weight: {weight*100:.0f}%)")
            else:
                print("⚠️ No valid scores from any API")
                overall_score = 0
            
            # ==========================================
            # 提取推荐建议
            # ==========================================
            print("\n💡 Extracting recommendations from agent responses...")
            
            all_recommendations_lists = []
            for response in agent_responses:
                recs = response.get('recommendations', [])
                if recs:
                    print(f"   {response.get('agent', 'Unknown')}: {len(recs)} recommendations")
                    all_recommendations_lists.append(recs)
            
            recommendations = merge_and_deduplicate_recommendations(all_recommendations_lists, max_total=12)
            print(f"✅ Total unique recommendations: {len(recommendations)}")
            
            # ==========================================
            # 生成改进的教案（如果分数较低）
            # ==========================================
            if overall_score < 70 and overall_score > 0:
                print(f"\n📝 Score {overall_score} below 70, generating improved lesson plan...")
                
                # ✅ 收集所有 strengths 和 areas
                all_strengths = []
                all_areas = []

                for agent_resp in agent_responses:
                    if agent_resp.get('analysis'):
                        for dim_key, dim_data in agent_resp['analysis'].items():
                            if dim_data.get('strengths'):
                                all_strengths.extend(dim_data['strengths'][:3])  # 每个维度取前3个
                            if dim_data.get('areas_for_improvement'):
                                all_areas.extend(dim_data['areas_for_improvement'][:3])
                
                # 去重
                all_strengths = list(dict.fromkeys(all_strengths))[:8]  # 最多8个
                all_areas = list(dict.fromkeys(all_areas))[:8]
                
                try:
                    # 更详细、更具体的 prompt
                    improvement_prompt = f"""You are a highly experienced educator in Aotearoa New Zealand. Your task is to significantly improve this lesson plan based on detailed evaluation feedback.
                    
                     **⚠️ CRITICAL OUTPUT FORMAT REQUIREMENT ⚠️**
You MUST write as a narrative lesson plan document, NOT as code or structured data.
❌ DO NOT use Python lists like ['item1', 'item2', 'item3']
❌ DO NOT use numbered sections like 1.1, 1.2, 2.1
❌ DO NOT format output as JSON or dictionary
✅ DO write in flowing narrative paragraphs like a real lesson plan
✅ DO write naturally as if you're a teacher writing for other teachers

═══════════════════════════════════════════════════════════
EXAMPLE OF CORRECT FORMAT (FOLLOW THIS STYLE):
═══════════════════════════════════════════════════════════

**IMPROVED LESSON PLAN: WAKA - CULTURALLY INTEGRATED**

**Overview:**
This improved lesson for upper primary students integrates three Te Reo Māori terms: waka (canoe/vessel), kaitiakitanga (environmental guardianship), and moana (ocean). Students will explore the cultural significance of waka for local iwi such as Ngāti Whātua (Auckland) or Ngāi Tahu (South Island), connect to local waterways like the Waitematā Harbour or Avon River, and critically examine whose maritime stories are usually told versus whose might be missing. They will compare Māori waka traditions with Pacific and global seafaring cultures.

**Learning Objectives:**
By the end of this lesson, students will be able to: First, use at least one Te Reo Māori term correctly with proper macrons, such as waka, moana, or kaitiakitanga, in both spoken and written contexts. Second, explain how waka connects to Māori cultural values like whanaungatanga (relationships) and whakapapa (genealogy). Third, identify at least two different perspectives on maritime traditions, such as Māori versus Pākehā views, or different iwi practices. Fourth, create a visual, oral, or written presentation demonstrating their understanding of waka's cultural significance.

[Continue in this flowing narrative style throughout...]

═══════════════════════════════════════════════════════════
NOW BEGIN YOUR ACTUAL IMPROVED LESSON PLAN:
═══════════════════════════════════════════════════════════

You are an experienced educator in Aotearoa New Zealand. Improve this lesson plan based on evaluation feedback.

**CRITICAL INSTRUCTIONS:**
⚠️ Write specific details, NOT generic templates
⚠️ Use actual names, NOT placeholders like "[local iwi]"
⚠️ Write in flowing narrative paragraphs, NOT bullet points or lists (except rubrics/resources)
⚠️ DO NOT use Python list format ['item1', 'item2']
⚠️ DO NOT use numbered sections like 1.1, 1.2, 2.1

═══════════════════════════════════════════════════════════
ORIGINAL LESSON
═══════════════════════════════════════════════════════════
Title: {title}
Grade: {grade_level or 'Not specified'}
Subject: {subject_area or 'Not specified'}

Original Plan: {text[:3000]}

═══════════════════════════════════════════════════════════
EVALUATION FEEDBACK
═══════════════════════════════════════════════════════════

**Scores:**
- Place-based: {place_based_score}/100
- Cultural Responsiveness: {cultural_score}/100
- Critical Pedagogy: {critical_pedagogy_score}/100
- Lesson Design: {lesson_design_score}/100
- Overall: {overall_score}/100

**Strengths:** {chr(10).join(f'✅ {{s}}' for s in all_strengths[:6]) if all_strengths else '(Limited strengths)'}

**Gaps:** {chr(10).join(f'❌ {{a}}' for a in all_areas[:6]) if all_areas else '(See recommendations)'}

**Recommendations:** {chr(10).join(f'{{i+1}}. {{rec}}' for i, rec in enumerate(recommendations[:10]))}

═══════════════════════════════════════════════════════════
REQUIREMENTS (REALISTIC & ACHIEVABLE)
═══════════════════════════════════════════════════════════

**1. TE REO MĀORI (MINIMUM 3 TERMS):**
✅ Include at least 3 Te Reo terms with correct macrons (ā, ē, ī, ō, ū)
✅ Students will use 1-2 terms to achieve "Achieving" level

**Choose from common terms:**
- Core: Aotearoa, Kia ora, Whānau, Mana, Aroha, Kia kaha
- ANZAC: Maumahara (remembrance), Pakanga (war), Kia kaha
- Matariki: Whetū (star), Kai (food), Whanaungatanga (relationships)
- Waitangi: Te Tiriti (Treaty), Rangatira (chief), Whenua (land)
- Kapa Haka: Waiata (song), Haka (dance), Mana
- Waka: Waka (canoe), Moana (ocean), Kaitiakitanga (guardianship)
- General: Tikanga (customs), Karakia (blessing), Marae (meeting grounds)

**Whakataukī (optional):**
- "Kia kaha, kia māia, kia manawanui" (Be strong, be brave, be steadfast)
- "He aha te mea nui? He tangata" (What is most important? People)
- "He waka eke noa" (A canoe we are all in together - for waka topics)

**2. CULTURAL UNDERSTANDING:**
✅ Explain 1-2 Māori cultural values (e.g., mana, whanaungatanga, kaitiakitanga)
✅ Show respect when discussing tapu (sacred) topics
✅ Acknowledge local iwi or Māori perspectives

**3. CRITICAL THINKING (1-2 QUESTIONS):**
Include at least ONE critical question like:
- "Whose stories do we usually hear about {title}?"
- "Why might different people have different feelings about {title}?"
- "How has {title} changed over time?"
- "Whose voices might be missing from this narrative?"

**4. PLACE-BASED (1-2 SPECIFIC PLACES):**
Name at least 1-2 actual local places (choose based on your region):
- **Auckland:** Ōrākei Marae, Auckland War Memorial Museum, Waitematā Harbour
- **Wellington:** Te Papa Museum, Pipitea Marae, Wellington Harbour
- **Canterbury:** Tuahiwi Marae, Canterbury Museum, Avon River
- **Bay of Plenty:** Ohinemutu Marae, Te Papaiouru Marae, Lake Rotorua
- **Northland:** Waitangi Treaty Grounds, Bay of Islands

**5. ACTIVITIES (2-4 WITH BASIC STEPS):**
Provide 2-4 activities written in narrative paragraph form with basic steps

**6. ASSESSMENT RUBRIC:**
Include this exact table:

| Criteria | Emerging (1) | Developing (2) | Achieving (3) | Exceeding (4) |
|----------|--------------|----------------|---------------|---------------|
| **Te Reo Māori** | 0 terms OR incorrect usage | 1-2 terms with errors in macrons | 1-2 terms used correctly with macrons | 3+ terms naturally integrated |
| **Cultural Understanding** | No cultural context | Basic cultural mention | Clear understanding of 1-2 concepts | Deep cultural analysis |
| **Critical Thinking** | Single viewpoint | Questions some ideas | Analyzes 2+ perspectives | Sophisticated analysis |
| **Content Knowledge** | Limited/inaccurate info | Some accurate content | Accurate, relevant content | Comprehensive, well-researched |
| **Presentation Quality** | Unclear or disorganized | Organized but needs polish | Clear and well-organized | Exceptionally engaging |

**7. RESOURCES (5-8 SPECIFIC):**
List specific resources with full details

**8. TIME ALLOCATION:**
Provide realistic time breakdown (60-90 minutes total)

═══════════════════════════════════════════════════════════
OUTPUT FORMAT - WRITE EXACTLY LIKE THIS:
═══════════════════════════════════════════════════════════

**IMPROVED LESSON PLAN: {title.upper()}**

**Overview:**
This improved lesson for {grade_level or 'upper primary'} students integrates at least three Te Reo Māori terms relevant to {title}, such as [write 3 actual terms like "waka, moana, kaitiakitanga" or "maumahara, pakanga, kia kaha"]. The lesson connects students to local places including [write 1-2 actual place names like "Auckland Museum and Ōrākei Marae" or "Te Papa Museum"]. Students will explore different cultural perspectives on {title}, understanding that Māori, Pacific, Pākehā, and other communities may have diverse experiences and viewpoints. They will critically examine whose stories are typically heard and whose voices might be marginalized in dominant narratives about {title}.

**Learning Objectives:**
By the end of this lesson, students will be able to achieve four key outcomes. First, they will correctly use at least one Te Reo Māori term with accurate macrons (ā, ē, ī, ō, ū) in both spoken and written contexts, demonstrating understanding of its cultural meaning beyond simple translation. Second, they will [write specific topic-related objective, such as "explain the cultural significance of waka for local iwi" or "identify key differences between Te Tiriti and the Treaty"]. Third, they will identify and analyze at least two different cultural or historical perspectives on {title}, recognizing that different communities have different relationships with this topic. Fourth, they will create a project—choosing from visual, oral, or written formats—that demonstrates their cultural understanding, uses Te Reo Māori appropriately, and presents multiple perspectives with respect and depth.

**Cultural Preparation:**
Before teaching this lesson, teachers should prepare by learning correct pronunciation of key Te Reo Māori terms at https://maoridictionary.co.nz, where audio recordings demonstrate proper vowel sounds and the importance of macrons. Teachers should consult with their school's Māori liaison teacher or cultural advisor to ensure lesson content is culturally appropriate and reflects local tikanga (protocols). If your school does not have a designated liaison, contact your regional Māori education coordinator or local marae for guidance. When opening the lesson, teachers can say: "Kia ora koutou (hello everyone). E mihi ana ki ngā mana whenua o tēnei rohe (We acknowledge the indigenous people of this place)." This simple acknowledgment shows respect for tangata whenua (indigenous people of the land) and sets a culturally respectful tone for learning.

**Lesson Activities:**

**Activity 1: [Write specific activity name relevant to topic] (20 minutes)**

The teacher begins the lesson by greeting students warmly: "Kia ora koutou katoa (hello to you all). Today we are exploring {title}, which in Te Reo Māori we can discuss using the word [write specific term with pronunciation guide, like 'waka (WAH-kah)' or 'maumahara (mow-mah-HAH-rah)']." The teacher writes this term on the board with correct macrons, explaining that macrons (the bar over vowels like ā, ē, ī, ō, ū) are not optional decorations but change the pronunciation and meaning of words. Students practice saying the word together three times, with the teacher gently correcting pronunciation as needed.

Next, the teacher displays [write specific visual aid and its source, such as "photographs of traditional waka from the Auckland Museum's online collection at www.aucklandmuseum.com" or "historical photos from NZ History website at https://nzhistory.govt.nz"]. The teacher gives students two minutes to pair-share, asking: "What do you notice in these images? What questions do you have?" After pair discussions, the teacher invites two or three students to share their partner's observations with the whole class, recording key ideas on chart paper.

The teacher then distributes [write specific handout with exact source]. For waka lessons, print the "Waka Types and Construction" information sheet from Te Ara Encyclopedia at https://teara.govt.nz/en/waka-canoes. For ANZAC lessons, print soldier profile cards from https://nzhistory.govt.nz/war/maori-battalion. For Matariki lessons, print a star chart from Te Papa's educational resources at https://www.tepapa.govt.nz/learn/for-educators/teaching-resources/matariki. For Waitangi lessons, print side-by-side excerpts of Te Tiriti and the English Treaty from https://nzhistory.govt.nz/politics/treaty.

Students work in small groups of three to four for fifteen minutes, discussing three guiding questions that the teacher writes clearly on the board: First, "What Te Reo Māori words appear in these materials, and what do they mean both in English translation and in cultural context?" Second, [write specific topic question like "How did waka design reflect the environment and resources available to different iwi?" or "Why might Māori soldiers have different motivations for service beyond 'duty to King and country'?"]. Third, "Whose perspective are we learning from in this material? Whose voices or stories might not be represented here?"

As groups work, the teacher circulates, listening carefully and asking follow-up questions to deepen thinking: "Can you explain what [specific Te Reo term] means culturally, not just the English translation?" or "What connections do you see between this story and Māori cultural values like mana or whanaungatanga?" After fifteen minutes, each group shares one key insight using this sentence frame written on the board: "We learned that [specific detail from materials]. This connects to the Māori cultural value of [Te Reo concept like mana, kaitiakitanga, or whanaungatanga] because [explanation of connection]." The teacher records these insights on chart paper, organizing them under cultural value headings.

For differentiation, the teacher provides multiple forms of support: Visual learners receive additional diagrams, maps, and photographs alongside text materials. Struggling readers access audio recordings of the handouts using text-to-speech tools or pre-recorded teacher readings. Advanced learners receive extension challenges such as researching additional examples or making connections to contemporary issues. English language learners receive vocabulary cards with the three key Te Reo terms, pictures, and simplified definitions before the lesson begins, allowing them to pre-learn essential vocabulary.

**[Write 1-3 more activities in same flowing narrative style, each 2-3 paragraphs]**

**Activity 2: Critical Discussion About Multiple Perspectives (10-15 minutes)**

The teacher transitions to a critical thinking discussion by posing this question to the class: "We've learned about {title} from certain perspectives today. Whose stories about {title} do we usually hear in schools, museums, and media? Whose voices or experiences might be less visible or harder to find?" The teacher gives students two minutes of silent thinking time, encouraging them to jot down initial ideas. Then students turn to a partner for three minutes of pair-share discussion, building on each other's thoughts.

The teacher facilitates a whole-class discussion, creating two columns on the whiteboard labeled "Voices Often Heard" and "Voices Less Heard." For a waka lesson, students might identify that Pākehā perspectives on maritime history dominate, while different iwi have diverse waka traditions that are often homogenized. For ANZAC lessons, students might note that male Pākehā soldiers' stories are most common, while Māori Battalion soldiers, women nurses, Pacific servicemen, or conscientious objectors receive less attention. For Waitangi lessons, students might recognize that government or Pākehā interpretations of the Treaty dominated for decades, while Māori understandings of Te Tiriti were systematically ignored.

The teacher asks: "Why might different groups of people—Māori versus Pākehā, different iwi like Ngāti Whātua versus Ngāi Tahu, urban versus rural communities, or younger versus older generations—have different feelings, memories, or perspectives about {title}?" Students discuss how historical context, cultural values, personal experiences, and the impacts of colonization shape how different communities relate to this topic. This discussion helps students understand that cultural knowledge is not monolithic and that seeking diverse perspectives enriches our understanding.

**Reflection and Closing (5-10 minutes)**

For the final reflection, students individually complete a brief written or verbal reflection depending on their age and preference. Younger students might turn to a new partner and complete these sentence starters aloud: "One Te Reo Māori word I learned today is [term], which means [translation] and is important because [cultural significance]. One thing I now understand about {title} is [key learning]. One question I still have is [question]." Older students might write a three-to-four sentence reflection in their journals addressing the same prompts.

The teacher closes the lesson with a synthesis statement: "Ka pai, everyone (well done). Today we learned that {title} is more than just [surface level understanding]. We discovered how Te Reo Māori words like [repeat 2-3 terms used] help us understand deeper cultural meanings. We also learned that different people and communities have different stories and perspectives about {title}, and that's okay—in fact, it's important. When we listen to multiple voices and honor diverse experiences, we develop richer, more respectful understanding. Ka kite ānō (until we meet again)."

**Assessment:**

Students will create [write specific project type, such as "a visual poster, oral presentation, or written report"] that demonstrates their understanding of {title}'s cultural significance. The assessment requires students to use at least one Te Reo Māori term correctly with proper macrons, explain its cultural meaning beyond simple translation, present at least two different cultural or historical perspectives on {title}, and communicate their learning clearly through their chosen format. Students may select from multiple presentation options: a visual poster incorporating Māori design elements, an oral presentation to the class, a written essay or report, a digital slideshow, or a creative project like a model or performance. This choice honors different learning styles and strengths while maintaining consistent learning expectations through the rubric.

**Assessment Rubric:**

| Criteria | Emerging (1) | Developing (2) | Achieving (3) | Exceeding (4) |
|----------|--------------|----------------|---------------|---------------|
| **Te Reo Māori Integration** | Uses 0 Te Reo terms OR uses terms incorrectly without macrons | Uses 1-2 terms with some errors in macrons or pronunciation | Uses 1-2 Te Reo terms correctly with accurate macrons (ā, ē, ī, ō, ū) | Uses 3+ terms naturally integrated throughout with perfect macrons |
| **Cultural Understanding** | No cultural context provided OR culturally insensitive | Basic cultural mention without depth | Clear understanding of 1-2 Māori cultural concepts with examples | Deep, nuanced cultural analysis demonstrating mātauranga Māori |
| **Critical Thinking** | Presents only single viewpoint | Questions some ideas but stays surface-level | Critically analyzes 2+ different perspectives with evidence | Sophisticated analysis of power, colonization, multiple voices |
| **Content Knowledge** | Limited or inaccurate information | Some accurate content but with gaps | Accurate, relevant, well-organized content | Comprehensive, exceptionally well-researched content |
| **Presentation Quality** | Unclear, disorganized, hard to follow | Organized but needs more polish or clarity | Clear, well-organized, and effectively presented | Exceptionally clear, engaging, and professionally presented |

Teachers assess each criterion on the 1-4 scale, total the scores (maximum 20 points), and convert to a percentage by dividing by twenty and multiplying by one hundred. Teachers also provide narrative feedback identifying specific strengths and growth areas, such as: "You used the term 'kaitiakitanga' correctly with perfect macrons and explained how it connects to environmental guardianship. To strengthen your work, try adding another perspective, such as how Pacific or Pākehā communities might view this topic differently."

**Resources:**

**Books:**
1. King, Michael. "The Penguin History of New Zealand." Penguin Books, 2003. ISBN: 978-0143018674. (Comprehensive NZ history with Māori perspectives)
2. [Add 1-2 topic-specific books with full citations]

**Videos:**
1. [Write specific video title] - Available at [exact URL like https://teara.govt.nz or https://www.rnz.co.nz]
2. [Add another relevant video if applicable]

**Websites:**
1. Māori Dictionary (https://maoridictionary.co.nz) - Essential for Te Reo pronunciation, definitions, and example sentences
2. Te Ara: The Encyclopedia of New Zealand (https://teara.govt.nz) - Comprehensive, authoritative information on NZ topics including extensive Māori content
3. NZ History (https://nzhistory.govt.nz) - Government history website with primary sources and educational resources
4. [Add 1-2 topic-specific websites with exact URLs]

**Community Resources:**
- Local marae: [Write specific marae name for your region, such as "Ōrākei Marae in Auckland (contact via www.orakeimarae.co.nz)" or "Tuahiwi Marae near Christchurch (Ngāi Tahu)"]
- Museum education programs: [Write specific program, such as "Auckland Museum's 'Māori Culture Gallery Tours' (www.aucklandmuseum.com/learn)" or "Te Papa's schools programs"]

**Time Allocation:**

This lesson is designed for a sixty-minute class period, though teachers can extend activities for a ninety-minute block if desired. The opening greeting and Te Reo introduction takes five to ten minutes, allowing time for pronunciation practice and cultural acknowledgment. Activity One runs for twenty minutes, including teacher explanation, group work, and sharing. Activity Two's critical discussion takes ten to fifteen minutes for pair-shares and whole-class synthesis. The closing reflection requires five to ten minutes for students to process and articulate their learning. Teachers should build in five to ten minutes of buffer time for transitions, questions, bathroom breaks, or extending discussions if students are deeply engaged. This flexible pacing ensures that all students can meaningfully participate without feeling rushed, while maintaining clear structure and expectations.

**Note to Teachers:**

This lesson plan should be reviewed by your school's Māori liaison teacher or cultural advisor before implementation to ensure cultural appropriateness for your specific school context and community. Teachers retain full responsibility for adapting content to their students' needs and honoring local tikanga (protocols) and iwi perspectives.

═══════════════════════════════════════════════════════════
SUCCESS CRITERIA - YOUR LESSON MUST MEET THESE:
═══════════════════════════════════════════════════════════

✅ Written in flowing narrative paragraphs (NOT Python lists or numbered sections)
✅ 1200-2000 words total
✅ At least 3 Te Reo Māori terms with correct macrons used naturally throughout
✅ 1-3 specific local places, resources, or people named (actual names, not placeholders)
✅ 2-4 activities described in narrative paragraph form with clear steps
✅ Complete rubric table included
✅ 5-8 specific resources listed with titles, authors, and URLs
✅ 1-2 critical thinking questions integrated into activities
✅ Addresses key gaps from evaluation feedback
✅ Immediately usable by teachers without further research

**NOW BEGIN WRITING YOUR IMPROVED LESSON PLAN IN FLOWING NARRATIVE PARAGRAPHS:**
"""

                    
                    print(f"📤 Sending improvement request to Claude ({len(improvement_prompt)} chars)...")
                    
                     # ✅ 添加详细日志
                    print("\n" + "="*60)
                    print("DEBUG: IMPROVEMENT PROMPT (first 1500 chars):")
                    print(improvement_prompt[:1500])
                    print("="*60 + "\n")

                    ai_response = await asyncio.wait_for(
                        llm_client.call("claude", improvement_prompt),
                        timeout=300  # Claude 需要更长时间，增加到 300s
                    )
                    
                    print(f"📥 Received response ({len(ai_response)} chars)")
                    #详细日志
                    print("\n" + "="*60)
                    print("DEBUG: AI RESPONSE (first 1500 chars):")
                    print(ai_response[:1500])
                    print("="*60 + "\n")

                    # ✅ 验证响应格式
                    if "1.1" in ai_response or "['Understanding" in ai_response or '["' in ai_response[:500]:
                        print("⚠️ Claude returned structured data format, attempting to reformat...")
                        
                        # 重新尝试，使用更强的指令
                        retry_prompt = f"""Your previous response was in WRONG FORMAT (Python lists/numbered sections).

                    DO NOT use this format:
                    1.1 Knowledge: ['item1', 'item2']
                    ❌ WRONG

                    USE this format instead:
                    **Learning Objectives:**
                    By the end of this lesson, students will understand...
                    ✅ CORRECT

                    Now rewrite the entire lesson plan in flowing narrative paragraphs:

                    {improvement_prompt}
                    """
                        
                        try:
                            ai_response = await asyncio.wait_for(
                                llm_client.call("claude", retry_prompt),
                                timeout=300
                            )
                            print(f"🔄 Retry response ({len(ai_response)} chars)")
                        except Exception as e:
                            print(f"❌ Retry failed: {e}, using original response")
                    
                    # 直接使用 AI 生成的文本 (不解析 JSON)
                    if ai_response and len(ai_response) > 500:
                        lesson_plan_text = ai_response.strip()
                        print(f"✅ Generated improved lesson plan ({len(lesson_plan_text)} chars)")
                        
                        # ✅ 新增：验证格式质量
                        validation = validate_lesson_format(lesson_plan_text)
                        
                        if validation["valid"]:
                            print("✅ Lesson plan format validation PASSED")
                            print(f"   📊 Stats: {validation['word_count']} words, {validation['char_count']} chars")
                            print(f"   ✅ Te Reo content: {validation['has_te_reo']}")
                            print(f"   ✅ Specific places: {validation['has_specific_places']}")
                            print(f"   ✅ Critical questions: {validation['has_critical_questions']}")
                        else:
                            print("⚠️ Lesson plan format validation FAILED")
                            print(f"   ❌ Issues found: {', '.join(validation['issues'])}")
                            if validation['warnings']:
                                print(f"   ⚠️ Warnings: {', '.join(validation['warnings'])}")
                        
                        # 验证质量
                        if "Te Reo" in lesson_plan_text or "Māori" in lesson_plan_text:
                            print("✅ Improved plan includes cultural content")
                        if any(keyword in lesson_plan_text.lower() for keyword in ['specific', 'example', 'activity', 'assessment']):
                            print("✅ Improved plan includes concrete details")
                    else:
                        print(f"⚠️ Generated plan too short ({len(ai_response)} chars), using original")
                        lesson_plan_text = text
                        
                except asyncio.TimeoutError:
                    print("⏱️ Lesson plan generation timeout after 300s")
                    lesson_plan_text = text
                except Exception as e:
                    print(f"❌ Lesson plan generation error: {str(e)}")
                    print(traceback.format_exc())
                    lesson_plan_text = text
            else:
                if overall_score == 0:
                    print(f"\n⚠️ No valid scores, skipping improvement generation")
                else:
                    print(f"\n✅ Score {overall_score} is good, no improvement needed")
                lesson_plan_text = text
            
        except asyncio.TimeoutError:
            print("❌ Overall evaluation timeout")
            raise HTTPException(status_code=504, detail="Evaluation timeout")
        except Exception as e:
            print(f"❌ Evaluation error: {str(e)}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
    

    else:
        # ==========================================
        # Mock mode - Framework v3.0
        # ✅ 更新为 4 个维度的 mock 数据
        # ==========================================
        print("\n🧪 Using MOCK mode with Framework v3.0 data")
        print("   4 Dimensions: PBL, CRMP (Integrated), CP, LDQ")
        print("="*60)
        
        place_based_score = 72
        cultural_score = 68  # ✅ 统一的文化维度分数
        critical_pedagogy_score = 75
        lesson_design_score = 78  # ✅ 新增
        
        # ✅ v3.0 权重: 0.25, 0.35, 0.25, 0.15
        weights = framework_loader.get_scoring_weights()
        dimension_scores = {
            'place_based_learning': place_based_score,
            'cultural_responsiveness_integrated': cultural_score,  # ✅ v3.0 key
            'critical_pedagogy': critical_pedagogy_score,
            'lesson_design_quality': lesson_design_score  # ✅ v3.0 新增
        }
        overall_score = calculate_weighted_score(dimension_scores, weights)
        
        print(f"📊 Mock Scores Generated:")
        print(f"   - Place-based Learning: {place_based_score}")
        print(f"   - Cultural Responsiveness (Integrated): {cultural_score}")
        print(f"   - Critical Pedagogy: {critical_pedagogy_score}")
        print(f"   - Lesson Design Quality: {lesson_design_score}")
        print(f"   - Overall: {overall_score}")
        
        agent_responses = [
            {
                "agent": "DeepSeek",
                "model": "deepseek-chat",
                "role": "Place-based Learning Specialist",
                "dimension": "place_based_learning",
                "response": "Mock evaluation - Place-based learning analysis with local context integration",
                "analysis": build_analysis_structure(
                    "place_based_learning", 
                    place_based_score, 
                    "Mock evaluation - This lesson shows good foundation in place-based learning.",
                    recommendations=[  # ✅ 具体建议（解决方案）
                        "Name specific local places (e.g., 'Waitematā Harbour' not just 'local waterway')",
                        "Partner with named local organizations (e.g., DOC Auckland office, local marae)",
                        "Design concrete fieldwork activities with step-by-step protocols",
                        "Connect to specific local environmental issues (e.g., kauri dieback in Waitakere Ranges)"
                    ],
                    strengths=[  # ✅ 优点（做得好的）
                        "Uses examples from the local community context",
                        "Encourages outdoor learning activities in nearby environments",
                        "Connects lesson content to regional geography and ecosystems",
                        "Shows awareness of place-based pedagogy principles"
                    ],
                    areas_for_improvement=[  # ✅ 需改进领域（问题陈述）- 与 recommendations 不同
                        "Local references are too generic - lacks specific named places or landmarks",
                        "Community partnerships mentioned but not detailed or actionable",
                        "Fieldwork activities described vaguely without clear procedures",
                        "Missing integration of local iwi environmental knowledge systems"
                    ],
                    gaps=[
                        "No specific local iwi or hapū partnerships identified",
                        "Indigenous ecological knowledge not incorporated",
                        "Community engagement is mentioned but not substantive"
                    ]
                ),
                "recommendations": [  # 与上面 recommendations 相同
                    "Name specific local places (e.g., 'Waitematā Harbour' not just 'local waterway')",
                    "Partner with named local organizations (e.g., DOC Auckland office, local marae)",
                    "Design concrete fieldwork activities with step-by-step protocols"
                ],
                "score": place_based_score,
                "time": 0.5
            },
            {
                "agent": "Claude",
                "model": "claude-sonnet-4-20250514",
                "role": "Cultural Responsiveness & Māori Perspectives Specialist (Integrated)",
                "dimension": "cultural_responsiveness_integrated",  #  v3.0 key
                "response": "Mock evaluation - Integrated cultural responsiveness and Māori perspectives analysis",
                "analysis": build_analysis_structure(
                    "cultural_responsiveness_integrated",  
                    cultural_score, 
                    "Mock evaluation - The lesson demonstrates cultural awareness and Māori integration in a unified approach.",
                    recommendations=[
                        "Include more Te Reo Māori vocabulary throughout",
                        "Consult with local iwi for cultural protocols",
                        "Add culturally diverse perspectives to content",
                        "Embed mātauranga Māori knowledge systems more deeply",
                        "Use appropriate karakia and mihi protocols"
                    ],
                    strengths=[
                        "Acknowledges cultural context of the topic",
                        "References tikanga Māori appropriately",
                        "Creates inclusive learning environment environment that values diversity",
                        "Shows respect for Māori worldviews and attempts integration",
                        "Includes some basic Te Reo Māori vocabulary beyond simple greetings"
                    ],
                    areas_for_improvement=[  # ✅ 需改进领域 (不同于 recommendations)
                        "Te Reo Māori usage is limited to basic greetings (kia ora, ka pai) - lacks subject-specific vocabulary",
                        "Mātauranga Māori is peripheral rather than central to curriculum design",
                        "Lacks depth in Māori philosophical concepts like whakapapa, mauri, or wairua",
                        "No evidence of iwi/hapū consultation or partnership in lesson development",
                        "Cultural diversity acknowledged but not deeply woven into pedagogy",
                        "Tikanga protocols (karakia, mihi) not explicitly included"
                    ],
                    gaps=[
                        "No consultation with local iwi mentioned",
                        "Missing karakia or cultural protocols",
                        "Could strengthen iwi consultation",
                        "Limited depth in Māori philosophical concepts"
                    ],
                    cultural_elements=[
                        "Basic Te Reo vocabulary: kia ora, ka pai, whānau",
                        "General tikanga references (not specific)",
                        "Acknowledgment of local iwi (name not specified)",
                        "Mention of cultural diversity (limited detail)"
                    ]
                ),
                "recommendations": [
                    "Include more Te Reo Māori vocabulary throughout",
                    "Consult with local iwi/hapū for cultural validation before implementation",
                    "Embed specific mātauranga Māori concepts as core content",
                    "Include a whakataukī relevant to lesson topic",
                    "Add explicit karakia or mihi protocols"
                ],
                "score": cultural_score,
                "time": 0.6
            },
            {
                "agent": "GPT-Critical",  #  v3.0: 区分名称
                "model": "gpt-4o",
                "role": "Critical Pedagogy Specialist",
                "dimension": "critical_pedagogy",
                "response": "Mock evaluation - Critical pedagogy and student engagement analysis",
                "analysis": build_analysis_structure(
                    "critical_pedagogy", 
                    critical_pedagogy_score, 
                    "Mock evaluation - The lesson shows good pedagogical strategies.",
                    recommendations=[  # ✅ 具体建议（解决方案）
                        "Add explicit critical questions that challenge dominant narratives (e.g., 'Whose stories are told? Whose are silenced?')",
                        "Provide genuine student choice in topics, research questions, and presentation formats",
                        "Include formative assessment with student self-reflection prompts and peer feedback",
                        "Design collaborative problem-solving tasks addressing real community issues",
                        "Incorporate diverse voices and perspectives (not just mainstream sources)"
                    ],
                    strengths=[  # ✅ 优点（做得好的）
                        "Uses questioning strategies to promote critical thinking",
                        "Includes student discussion opportunities throughout the lesson",
                        "Offers some choice in learning activities and assessment formats",
                        "Shows awareness of active learning principles",
                        "Attempts to engage students in meaningful dialogue"
                    ],
                    areas_for_improvement=[  # ✅ 需改进领域（问题陈述）- 与 recommendations 不同
                        "Student voice in decision-making is limited - teacher maintains heavy control",
                        "Critical analysis of power structures and dominant narratives is minimal",
                        "Assessment is mostly teacher-directed with limited student agency",
                        "Social justice themes are absent or superficial",
                        "Questioning tends toward closed-ended rather than open critical inquiry",
                        "Student choice is token rather than substantive"
                    ],
                    gaps=[
                        "No explicit examination of power dynamics or systemic issues",
                        "Missing critical questions about whose knowledge is valued",
                        "Limited connection to students' lived experiences and community realities",
                        "No action-oriented component (praxis)"
                    ]
                ),
                "recommendations": [  # 与上面 recommendations 相同
                    "Add explicit critical questions challenging dominant narratives",
                    "Provide genuine student choice in topics and methods",
                    "Include formative assessment with student self-reflection",
                    "Design collaborative problem-solving tasks"
                ],
                "score": critical_pedagogy_score,
                "time": 0.4
            },
            {
                "agent": "GPT-Design",  # ✅ v3.0: 新增 Agent 4
                "model": "gpt-4o",
                "role": "Lesson Design & Quality Specialist",
                "dimension": "lesson_design_quality",  # ✅ v3.0: 新维度
                "response": "Mock evaluation - Lesson design quality and structural coherence analysis (Framework v3.0)",
                "analysis": build_analysis_structure(
                    "lesson_design_quality",
                    lesson_design_score,
                    "Mock evaluation - The lesson plan shows good instructional design quality.",
                    recommendations=[  # ✅ 具体建议（解决方案）
                        "Develop detailed rubrics with clear success criteria for each learning objective",
                        "Add explicit differentiation strategies: tiered activities, flexible grouping, varied scaffolds",
                        "Strengthen alignment between stated objectives and assessment methods",
                        "Improve time allocation realism - add buffer time for transitions and unexpected needs",
                        "Provide more specific instructional guidance (step-by-step procedures for teachers)"
                    ],
                    strengths=[  # ✅ 优点（做得好的）
                        "Learning objectives are clearly stated and measurable",
                        "Lesson has logical flow and coherent structure (intro-main-conclusion)",
                        "Uses varied instructional strategies (discussion, group work, individual tasks)",
                        "Identifies appropriate resources and materials for the lesson",
                        "Shows understanding of backward design principles"
                    ],
                    areas_for_improvement=[  # ✅ 需改进领域（问题陈述）- 与 recommendations 不同
                        "Assessment criteria are vague - lacks explicit rubrics or success criteria",
                        "Differentiation is limited - minimal scaffolding for diverse learners",
                        "Time estimates may be unrealistic for the planned activities",
                        "Alignment between objectives and assessments could be stronger",
                        "Instructional guidance lacks detail - difficult for another teacher to implement",
                        "Limited variety in assessment methods (mostly traditional)"
                    ],
                    gaps=[
                        "No explicit rubrics or scoring guides provided",
                        "Missing scaffolds for struggling learners",
                        "Extensions for advanced learners not specified",
                        "Transitions between activities not detailed"
                    ]
                ),
                "recommendations": [  # 与上面 recommendations 相同
                    "Develop detailed rubrics with clear success criteria",
                    "Add explicit differentiation strategies for diverse learners",
                    "Strengthen alignment between objectives and assessments",
                    "Improve time allocation with buffer for transitions"
                ],
                "score": lesson_design_score,
                "time": 0.3
            }
        ]
        
        recommendations = [
            "Strengthen local context integration with specific regional examples",
            "Include more Te Reo Māori vocabulary throughout",
            "Enhance student agency with more choice in learning activities",
            "Add community partnerships with local organizations",
            "Consult with local iwi for cultural protocols",
            "Embed mātauranga Māori knowledge systems more deeply",
            "Add explicit rubrics with clear success criteria",
            "Include fieldwork opportunities in nearby environments",
            "Use appropriate karakia and mihi protocols",
            "Strengthen alignment between objectives and assessments",
            "Add formative assessment with student self-reflection",
            "Include more differentiation strategies for diverse learners"
        ]
        
        lesson_plan_text = text
    
    # ==========================================
    # 保存到数据库
    # ==========================================
    try:
        print(f"\n💾 Saving evaluation to database...")
        
        eval_id = db.create_evaluation(
            lesson_plan_text=text,
            lesson_plan_title=title,
            grade_level=grade_level,
            subject_area=subject_area,
            api_mode=API_MODE
        )
        
        # ✅ 保存所有 4 个维度的分数
        db.update_evaluation_scores(
            eval_id=eval_id,
            place_based_score=place_based_score,
            cultural_score=cultural_score,
            overall_score=overall_score
        )
        
        db.update_evaluation_results(
            eval_id=eval_id,
            agent_responses=agent_responses,
            debate_transcript={},
            recommendations=recommendations,
            status="completed"
        )
        
        print(f"✅ Evaluation saved successfully (ID: {eval_id})")
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        print(traceback.format_exc())
    
    # ==========================================
    # 返回结果
    # ✅ Framework v3.0: 4 个维度
    # ==========================================
    return {
        "status": "success",
        "evaluation_id": eval_id,
        "agent_responses": agent_responses,
        "recommendations": recommendations,
        "scores": {
            "place_based_learning": place_based_score,
            "cultural_responsiveness_integrated": cultural_score,  # ✅ v3.0 key
            "critical_pedagogy": critical_pedagogy_score,
            "lesson_design_quality": lesson_design_score,  # ✅ v3.0 新增
            "overall": overall_score
        },
        "framework_info": {
            "weights_applied": framework_loader.get_scoring_weights(),
            "dimensions_evaluated": [
                "place_based_learning",
                "cultural_responsiveness_integrated",  # ✅ v3.0 key
                "critical_pedagogy",
                "lesson_design_quality"  # ✅ v3.0 新增
            ],
            "framework_version": framework_loader.load_theoretical_framework()
                                .get('framework_metadata', {})
                                .get('version', '3.0'),
            "apis_used": {
                "deepseek": ENABLE_DEEPSEEK and place_based_score > 0,
                "claude": ENABLE_CLAUDE and cultural_score > 0,
                "gpt": ENABLE_GPT and (critical_pedagogy_score > 0 or lesson_design_score > 0)
            }
        },
        "improved_lesson_plan": lesson_plan_text,
        "mode": API_MODE
    }


@app.post("/api/improve-lesson")
@timing_decorator
async def improve_lesson(request: ImproveLessonRequest):
    """改进教案端点 - Framework v3.0 - 使用 Claude 生成叙述型教案（不再使用 TEMPLATE）"""
    try:
        print(f"\n📝 Improve Lesson Request (Framework v3.0)")
        print(f"   Title: {request.lesson_title}")
        print(f"   Grade: {request.grade_level}")
        print(f"   Recommendations: {len(request.recommendations)}")
        
        # 构建 Claude 专用的叙述型 prompt
        improvement_prompt = f"""***CRITICAL: YOU ARE CLAUDE, WRITING A NARRATIVE LESSON PLAN***

        ⚠️You MUST write in flowing narrative paragraphs, NOT code or structured data.

❌ DO NOT output:
- Python lists: ['item1', 'item2']
- Numbered sections: 1.1, 1.2, 2.1
- JSON format or dictionary structure
- Any code-like format

✅ DO output:
- Flowing narrative paragraphs written naturally
- Professional teacher-to-teacher writing style
- Start immediately with: **IMPROVED LESSON PLAN: {request.lesson_title.upper()}**

═══════════════════════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════════════════════

**Title:** {request.lesson_title}
**Grade Level:** {request.grade_level or 'Not specified'}
**Subject:** {request.subject_area or 'Not specified'}

**Current Scores:**
{json.dumps(request.scores, indent=2)}

**Key Recommendations to Address:**
{chr(10).join(f'{i+1}. {rec}' for i, rec in enumerate(request.recommendations[:10]))}

**Original Lesson Plan (excerpt):**
{request.original_lesson[:3000]}

═══════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════

Generate an improved lesson plan (1200-2000 words) in flowing narrative paragraphs that:

1. **Integrates 3+ Te Reo Māori terms** with correct macrons (ā, ē, ī, ō, ū)
   - Choose from: Kia ora, Whānau, Mana, Aroha, Kaitiakitanga, Whanaungatanga, etc.
   - Students use 1-2 terms to achieve "Achieving" level

2. **Names 1-2 specific local places**
   - Auckland: Ōrākei Marae, Auckland Museum, Waitematā Harbour
   - Wellington: Te Papa Museum, Pipitea Marae
   - Canterbury: Tuahiwi Marae, Canterbury Museum
   - Bay of Plenty: Ohinemutu Marae, Lake Rotorua
   - Northland: Waitangi Treaty Grounds

3. **Includes 1-2 critical thinking questions**
   - "Whose stories do we usually hear about {request.lesson_title}?"
   - "Why might different people have different feelings about this topic?"
   - "Whose voices might be missing from this narrative?"

4. **Provides 2-3 activities** with clear steps in narrative form

5. **Includes assessment rubric** (table format is OK for rubric only)

6. **Lists 5-8 specific resources** with titles and URLs

═══════════════════════════════════════════════════════════
OUTPUT FORMAT - WRITE EXACTLY LIKE THIS
═══════════════════════════════════════════════════════════

**IMPROVED LESSON PLAN: {request.lesson_title.upper()}**

**Overview:**
This improved lesson for {request.grade_level or 'upper primary'} students integrates three Te Reo Māori terms: [write 3 specific terms like "whānau (family), mana (prestige), kaitiakitanga (guardianship)"]. The lesson connects students to local places such as [write 1-2 actual place names like "Auckland Museum and Ōrākei Marae"]. Students will explore different cultural perspectives on {request.lesson_title}, understanding that Māori, Pacific, Pākehā, and other communities may have diverse experiences. They will critically examine whose stories are typically heard and whose voices might be marginalized.

**Learning Objectives:**
By the end of this lesson, students will achieve four key outcomes. First, they will correctly use at least one Te Reo Māori term with accurate macrons in both spoken and written contexts. Second, they will [write specific topic-related objective]. Third, they will identify and analyze at least two different perspectives on {request.lesson_title}. Fourth, they will create a project demonstrating their cultural understanding.

**Cultural Preparation:**
Before teaching this lesson, teachers should learn correct pronunciation of key Te Reo Māori terms at https://maoridictionary.co.nz. Teachers should consult with their school's Māori liaison teacher or cultural advisor to ensure cultural appropriateness. When opening the lesson, teachers can say: "Kia ora koutou. E mihi ana ki ngā mana whenua o tēnei rohe" (Hello everyone. We acknowledge the indigenous people of this place).

**Lesson Activities:**

**Activity One: [Specific Activity Name] (20 minutes)**

The teacher begins by greeting students: "Kia ora koutou katoa. Today we explore {request.lesson_title}. In Te Reo, we can discuss this using the word [specific term with pronunciation]." The teacher writes this term on the board with correct macrons, explaining their importance. Students practice saying the word together three times.

The teacher displays [specific visual aid from specific source like "photographs from Auckland Museum's collection at www.aucklandmuseum.com"]. Students pair-share for two minutes: "What do you notice? What questions arise?" The teacher invites three students to share observations.

The teacher distributes [specific handout from exact source]. For example, print information sheets from Te Ara Encyclopedia at https://teara.govt.nz. Students work in small groups of three to four for fifteen minutes, discussing three questions written on the board: What Te Reo words appear? [Topic-specific question]? Whose perspectives are represented?

As groups work, the teacher circulates asking follow-up questions: "Can you explain what this term means culturally, not just the English translation?" After fifteen minutes, each group shares one insight using the sentence frame: "We learned [detail]. This connects to [cultural value] because [explanation]."

For differentiation, visual learners receive additional diagrams and photographs. Struggling readers access audio recordings of materials. Advanced learners research additional examples. English language learners receive vocabulary cards with the three key Te Reo terms before the lesson begins.

**[Write 1-2 more activities in same flowing narrative style]**

**Activity Two: Critical Discussion About Multiple Perspectives (10-15 minutes)**

The teacher transitions to critical thinking by posing: "Whose stories about {request.lesson_title} do we usually hear in schools and media? Whose voices might be less visible?" Students have two minutes of silent thinking, then three minutes of pair-share discussion.

The teacher facilitates whole-class discussion, creating two columns on the whiteboard: "Voices Often Heard" and "Voices Less Heard." Students might identify that [give specific examples relevant to topic]. The teacher asks: "Why might different groups have different perspectives?" Students discuss how historical context, cultural values, and personal experiences shape understanding.

**Reflection and Closing (5-10 minutes)**

Students complete a brief reflection. Younger students might turn to a partner and say: "One Te Reo word I learned is [term], which means [translation] and matters because [significance]. I now understand that {request.lesson_title} [key learning]. My question is [question]." Older students write three to four sentences addressing the same prompts.

The teacher closes: "Ka pai, everyone. Today we learned that {request.lesson_title} involves deeper cultural meanings. We discovered how Te Reo words like [repeat terms] help us understand these meanings. We also learned that different communities have different stories, and seeking diverse perspectives enriches our understanding. Ka kite ānō."

**Assessment:**

Students will create [specific project type like "a visual poster, oral presentation, or written report"] demonstrating understanding of {request.lesson_title}'s cultural significance. The assessment requires using at least one Te Reo Māori term correctly with proper macrons, explaining its cultural meaning, presenting at least two different perspectives, and communicating clearly. Students may choose from multiple formats: visual poster, oral presentation, written essay, digital slideshow, or creative project.

**Assessment Rubric:**

| Criteria | Emerging (1) | Developing (2) | Achieving (3) | Exceeding (4) |
|----------|--------------|----------------|---------------|---------------|
| **Te Reo Māori** | 0 terms OR incorrect | 1-2 terms with errors | 1-2 terms correct with macrons | 3+ terms naturally integrated |
| **Cultural Understanding** | No cultural context | Basic mention | Clear understanding of 1-2 concepts | Deep cultural analysis |
| **Critical Thinking** | Single viewpoint | Questions some ideas | Analyzes 2+ perspectives | Sophisticated analysis |
| **Content Knowledge** | Limited/inaccurate | Some accurate content | Accurate, relevant content | Comprehensive research |
| **Presentation Quality** | Unclear | Organized but needs polish | Clear and well-organized | Exceptionally engaging |

**Resources:**

**Books:**
1. King, Michael. "The Penguin History of New Zealand." Penguin Books, 2003.
2. [Add 1-2 topic-specific books]

**Videos:**
1. [Topic video] - Available at [URL]

**Websites:**
1. Māori Dictionary (https://maoridictionary.co.nz) - Te Reo pronunciation
2. Te Ara Encyclopedia (https://teara.govt.nz) - NZ topics
3. NZ History (https://nzhistory.govt.nz) - Historical resources
4. [Add 1-2 topic-specific sites]

**Community:**
- Local marae: [Specific marae name like "Ōrākei Marae in Auckland"]
- Museum: [Specific education program]

**Time Allocation:**

This lesson is designed for sixty minutes. The opening takes five to ten minutes for greeting and Te Reo introduction. Activity One runs for twenty minutes including explanation, group work, and sharing. Activity Two's critical discussion takes ten to fifteen minutes. The closing reflection requires five to ten minutes. Teachers should build in five minutes buffer time for transitions and questions.

**Note to Teachers:**

This lesson plan should be reviewed by your school's Māori liaison teacher before implementation to ensure cultural appropriateness for your specific context.

═══════════════════════════════════════════════════════════

NOW BEGIN WRITING YOUR IMPROVED LESSON PLAN IN FLOWING NARRATIVE PARAGRAPHS:
"""
        
        print(f"📤 Sending to Claude ({len(improvement_prompt)} chars)...")
        
        llm_client = LLMClient()
        
        # ✅ 使用 Claude，不是 ChatGPT
        response = await asyncio.wait_for(
            llm_client.call("claude", improvement_prompt),
            timeout=300  # ✅ Claude 需要更长时间
        )
        
        print(f"📥 Received Claude response ({len(response)} chars)")
        
        # ✅ 直接使用 Claude 的响应，不解析 JSON，不用 TEMPLATE
        improved_lesson = response.strip()
        
        #  使用验证函数验证格式
        validation = validate_lesson_format(improved_lesson)

        if validation["valid"]:
            print("✅ Lesson plan format validation PASSED")
            print(f"   📊 Stats: {validation['word_count']} words")
            print(f"   ✅ Te Reo: {validation['has_te_reo']}")
            print(f"   ✅ Places: {validation['has_specific_places']}")
            print(f"   ✅ Critical thinking: {validation['has_critical_questions']}")
        else:
            print("⚠️ Lesson plan format validation FAILED")
            print(f"   ❌ Issues: {', '.join(validation['issues'])}")
            
            # 如果有严重问题，可以选择拒绝或标记
            if "numbered sections" in ' '.join(validation['issues']).lower():
                print("   🔧 Attempting to clean numbered sections...")
                # 可以在这里添加清理逻辑

        if validation['warnings']:
            print(f"   ⚠️ Warnings: {', '.join(validation['warnings'])}")
        
        return {
            "status": "success",
            "improved_lesson": improved_lesson,
            "original_title": request.lesson_title,
            "recommendations_applied": len(request.recommendations),
            "framework_version": "3.0",
            "generator": "claude",  # ✅ 标识使用 Claude
            "word_count": len(improved_lesson.split())
        }
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Claude improvement generation timeout after 300s")
    except Exception as e:
        print(f"❌ Error improving lesson: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Improvement failed: {str(e)}")


@app.post("/api/convert-to-word")
async def convert_to_word(request: dict):
    """将教案转换为 Word 文档"""
    try:
        from docx import Document
        from io import BytesIO
        
        doc = Document()
        doc.add_heading(request.get('title', 'Improved Lesson Plan'), 0)
        
        content = request.get('content', '')
        for paragraph in content.split('\n'):
            if paragraph.strip():
                doc.add_paragraph(paragraph)
        
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=Improved_Lesson_Plan.docx"
            }
        )
        
    except Exception as e:
        print(f"❌ Word conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/evaluations")
async def get_evaluations(
    limit: int = 20,
    offset: int = 0,
    db: Database = Depends(get_db)
):
    """获取历史评估记录列表"""
    try:
        print(f"\n📚 Fetching evaluations: limit={limit}, offset={offset}")
        
        evaluations = db.get_all_evaluations(limit=limit)
        
        if not evaluations:
            print("ℹ️ No evaluations found in database")
            return {
                "status": "success",
                "evaluations": [],
                "count": 0
            }
        
        print(f"✅ Retrieved {len(evaluations)} evaluations")
        
        formatted_evaluations = []
        for eval_record in evaluations:
            try:
                agent_responses = json.loads(eval_record.get("agent_responses", "[]"))
                recommendations = json.loads(eval_record.get("recommendations", "[]"))
            except:
                agent_responses = []
                recommendations = []
            
            # ✅ Framework v3.0: 4 个维度
            scores = {
                "place_based_learning": eval_record.get("place_based_score", 0),
                "cultural_responsiveness_integrated": eval_record.get("cultural_score", 0),
                "critical_pedagogy": eval_record.get("critical_pedagogy_score", 0),
                "lesson_design_quality": eval_record.get("lesson_design_score", 0)
            }
            
            formatted_evaluations.append({
                "id": eval_record.get("id"),
                "lesson_title": eval_record.get("lesson_plan_title") or eval_record.get("lesson_title", "Untitled"),
                "grade_level": eval_record.get("grade_level", "N/A"),
                "subject_area": eval_record.get("subject_area", "N/A"),
                "overall_score": eval_record.get("overall_score", 0),
                "scores": scores,
                "created_at": eval_record.get("created_at"),
                "status": eval_record.get("status", "completed"),
                "mode": eval_record.get("api_mode", "real"),
                "framework_version": "3.0"
            })
        
        return {
            "status": "success",
            "evaluations": formatted_evaluations,
            "count": len(formatted_evaluations)
        }
        
    except Exception as e:
        print(f"❌ Error fetching evaluations: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "success",
            "evaluations": [],
            "count": 0
        }


@app.get("/api/evaluations/{evaluation_id}")
async def get_evaluation_by_id(
    evaluation_id: int,
    db: Database = Depends(get_db)
):
    """获取单个评估记录的详细信息"""
    try:
        print(f"\n🔍 Fetching evaluation ID: {evaluation_id}")
        
        evaluation = db.get_evaluation(evaluation_id)
        
        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation {evaluation_id} not found"
            )
        
        print(f"✅ Retrieved evaluation: {evaluation.get('lesson_plan_title', 'Untitled')}")
        
        try:
            evaluation["agent_responses"] = json.loads(evaluation.get("agent_responses", "[]"))
        except:
            evaluation["agent_responses"] = []
        
        try:
            evaluation["recommendations"] = json.loads(evaluation.get("recommendations", "[]"))
        except:
            evaluation["recommendations"] = []
        
        try:
            evaluation["debate_transcript"] = json.loads(evaluation.get("debate_transcript", "{}"))
        except:
            evaluation["debate_transcript"] = {}
        
        return {
            "status": "success",
            "evaluation": evaluation,
            "framework_version": "3.0"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching evaluation: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve evaluation: {str(e)}"
        )


@app.delete("/api/evaluations/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: int,
    db: Database = Depends(get_db)
):
    """删除指定的评估记录"""
    try:
        print(f"\n🗑️ Deleting evaluation ID: {evaluation_id}")
        
        evaluation = db.get_evaluation(evaluation_id)
        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation {evaluation_id} not found"
            )
        
        db.delete_evaluation(evaluation_id)
        
        print(f"✅ Deleted evaluation ID: {evaluation_id}")
        
        return {
            "status": "success",
            "message": f"Evaluation {evaluation_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting evaluation: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete evaluation: {str(e)}"
        )


# ==========================================
# 启动信息
# ==========================================
print("\n" + "="*60)
print("🚀 Lesson Plan Evaluator API - Framework v3.0")
print("="*60)

try:
    framework = framework_loader.load_theoretical_framework()
    framework_name = framework.get('framework_metadata', {}).get('name', 'Default')
    framework_version = framework.get('framework_metadata', {}).get('version', '3.0')
    dimensions = list(framework.get('dimensions', {}).keys())
    
    print(f"📚 Framework: {framework_name} (v{framework_version})")
    print(f"📊 Dimensions: {len(dimensions)}")
    for dim in dimensions:
        print(f"   • {dim}")
    print(f"🤖 API Mode: {API_MODE}")
    print(f"💾 Database: Connected")
    
    agent_design = framework_loader.load_agent_design()
    agents = agent_design.get('agents', {})
    print(f"\n🎯 Configured Agents ({len(agents)}):")
    for agent_id, agent_info in agents.items():
        status = "✅" if (
            (agent_info['name'] == 'DeepSeek' and ENABLE_DEEPSEEK) or
            (agent_info['name'] == 'Claude' and ENABLE_CLAUDE) or
            (agent_info['name'] in ['GPT-Critical', 'GPT-Design'] and ENABLE_GPT)
        ) else "⚠️ DISABLED"
        print(f"   {status} {agent_info['name']}: {agent_info['role']}")
    
    weights = framework_loader.get_scoring_weights()
    print(f"\n⚖️  Scoring Weights (v3.0):")
    for dim, weight in weights.items():
        print(f"   • {dim}: {weight*100:.0f}%")
    
    print(f"\n🔧 API Configuration:")
    print(f"   • DeepSeek: {'Enabled' if ENABLE_DEEPSEEK else 'Disabled'}")
    print(f"   • Claude: {'Enabled' if ENABLE_CLAUDE else 'Disabled'}")
    print(f"   • GPT: {'Enabled' if ENABLE_GPT else 'Disabled'}")
    print(f"   • Timeout: {API_TIMEOUT}s")
    print(f"   • Max Retries: {API_MAX_RETRIES}")
    print(f"   • Retry Delay: {API_RETRY_DELAY}s")
    
except Exception as e:
    print(f"⚠️ Warning: Could not load framework details: {e}")

print("="*60)
print("✅ API is ready to accept requests!")
print("📍 Endpoints:")
print("   • GET  / - API info")
print("   • GET  /api/framework - Framework details")
print("   • POST /api/evaluate/lesson - Evaluate lesson plan")
print("   • POST /api/improve-lesson - Generate improved lesson")
print("   • GET  /api/evaluations - Get evaluation history")
print("="*60 + "\n")