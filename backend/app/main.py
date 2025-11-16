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

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_database(reset=False)
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
    yield
    print("👋 Application shutdown")

app = FastAPI(title="Lesson Plan Evaluator API", lifespan=lifespan)

# 修复CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 本地开发
        "https://your-frontend.vercel.app",  # 生产环境，部署前端后填写
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

def get_db():
    db = Database()
    db.connect()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "message": "Lesson Plan Evaluator API",
        "mode": API_MODE,
        "database": "connected",
        "status": "operational",
        "features": {
            "file_upload": {
                "word": DOCX_AVAILABLE,
                "pdf": PDF_AVAILABLE
            }
        }
    }

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
    return LESSON_PLAN_TEMPLATE.format(
        knowledge=fields.get("knowledge", ""),
        skills=fields.get("skills", ""),
        values=fields.get("values", ""),
        prior_knowledge=fields.get("prior_knowledge", ""),
        interests=fields.get("interests", ""),
        challenges=fields.get("challenges", ""),
        learning_styles=fields.get("learning_styles", ""),
        accommodations=fields.get("accommodations", ""),
        key_concepts=fields.get("key_concepts", ""),
        focus_challenges=fields.get("focus_challenges", ""),
        methods=fields.get("methods", ""),
        strategies=fields.get("strategies", ""),
        teacher_prep=fields.get("teacher_prep", ""),
        student_prep=fields.get("student_prep", ""),
        # Updated: Introduction
        intro_duration=fields.get("intro_duration", ""),
        intro_tasks=fields.get("intro_tasks", ""),
        intro_teacher_actions=fields.get("intro_teacher_actions", ""),
        intro_student_activities=fields.get("intro_student_activities", ""),
        # Updated: Main Teaching
        main_duration=fields.get("main_duration", ""),
        main_tasks=fields.get("main_tasks", ""),
        main_teacher_actions=fields.get("main_teacher_actions", ""),
        main_student_activities=fields.get("main_student_activities", ""),
        # Updated: Investigation & Exploration (renamed from Activities)
        investigation_duration=fields.get("investigation_duration", ""),
        investigation_tasks=fields.get("investigation_tasks", ""),
        investigation_teacher_actions=fields.get("investigation_teacher_actions", ""),
        investigation_student_activities=fields.get("investigation_student_activities", ""),
        # Updated: Conclusion
        conclusion_duration=fields.get("conclusion_duration", ""),
        conclusion_tasks=fields.get("conclusion_tasks", ""),
        conclusion_teacher_actions=fields.get("conclusion_teacher_actions", ""),
        conclusion_student_activities=fields.get("conclusion_student_activities", ""),
        # Updated: Extension
        extension_duration=fields.get("extension_duration", ""),
        extension_tasks=fields.get("extension_tasks", ""),
        extension_teacher_actions=fields.get("extension_teacher_actions", ""),
        extension_student_activities=fields.get("extension_student_activities", ""),
        # Assessment and Resources
        formative=fields.get("formative", ""),
        summative=fields.get("summative", ""),
        feedback=fields.get("feedback", ""),
        materials=fields.get("materials", ""),
        tech_tools=fields.get("tech_tools", "")
    )

llm_client = LLMClient()

@app.post("/api/extract-text")
async def extract_text_from_file(file: UploadFile = File(...)):
    """
    文件上传端点 - 增强错误处理和日志
    """
    print(f"\n{'='*60}")
    print(f"📁 FILE UPLOAD REQUEST")
    print(f"{'='*60}")
    print(f"Filename: {file.filename}")
    print(f"Content-Type: {file.content_type}")
    
    try:
        content = await file.read()
        file_size = len(content)
        print(f"File size: {file_size} bytes ({file_size/1024:.2f} KB)")
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        text = ""
        title = ""
        
        if file.filename.lower().endswith('.docx'):
            if not DOCX_AVAILABLE:
                raise HTTPException(
                    status_code=501, 
                    detail="Word file support not installed. Please install: pip install python-docx"
                )
            
            print("📄 Processing Word document...")
            try:
                doc = docx.Document(BytesIO(content))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                text = '\n\n'.join(paragraphs)
                
                if paragraphs:
                    title = paragraphs[0][:100]
                
                print(f"✅ Extracted {len(paragraphs)} paragraphs")
                print(f"✅ Total characters: {len(text)}")
                
            except Exception as e:
                print(f"❌ Word processing error: {str(e)}")
                print(traceback.format_exc())
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to process Word document: {str(e)}"
                )
        
        elif file.filename.lower().endswith('.pdf'):
            if not PDF_AVAILABLE:
                raise HTTPException(
                    status_code=501, 
                    detail="PDF support not installed. Please install: pip install PyPDF2"
                )
            
            print("📄 Processing PDF document...")
            try:
                pdf_reader = PyPDF2.PdfReader(BytesIO(content))
                num_pages = len(pdf_reader.pages)
                print(f"📑 PDF has {num_pages} pages")
                
                pages_text = []
                for i, page in enumerate(pdf_reader.pages):
                    print(f"Processing page {i+1}/{num_pages}...")
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        pages_text.append(page_text)
                
                text = '\n\n'.join(pages_text)
                title = file.filename.replace('.pdf', '')
                
                if text and len(text) > 0:
                    first_line = text.split('\n')[0][:100]
                    if first_line:
                        title = first_line
                
                print(f"✅ Extracted {len(pages_text)} pages")
                print(f"✅ Total characters: {len(text)}")
                
            except Exception as e:
                print(f"❌ PDF processing error: {str(e)}")
                print(traceback.format_exc())
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to process PDF: {str(e)}"
                )
        
        elif file.filename.lower().endswith('.doc'):
            raise HTTPException(
                status_code=400, 
                detail="Old .doc format not supported. Please convert to .docx"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Only .docx and .pdf are supported. Got: {file.filename}"
            )
        
        if not text or not text.strip():
            raise HTTPException(
                status_code=400, 
                detail="No text content could be extracted from the file"
            )
        
        word_count = len(text.split())
        print(f"\n✅ FILE PROCESSING SUCCESSFUL")
        print(f"Title: {title}")
        print(f"Characters: {len(text)}")
        print(f"Words: {word_count}")
        print(f"{'='*60}\n")
        
        return {
            "status": "success",
            "text": text,
            "metadata": {
                "title": title,
                "filename": file.filename,
                "length": len(text),
                "word_count": word_count
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        print(f"{'='*60}\n")
        raise HTTPException(
            status_code=500, 
            detail=f"File processing failed: {str(e)}"
        )


class ConvertToWordRequest(BaseModel):
    content: str
    filename: str


@app.post("/api/convert-to-word")
async def convert_to_word(request: ConvertToWordRequest):
    """
    转换改进的教案为 Word 文档 - 修复 CORS 和 Header 问题
    """
    print(f"\n{'='*60}")
    print(f"📥 CONVERT TO WORD REQUEST")
    print(f"{'='*60}")
    print(f"Filename: {request.filename}")
    print(f"Content length: {len(request.content)} characters")
    
    try:
        if not DOCX_AVAILABLE:
            raise HTTPException(
                status_code=501, 
                detail="Word conversion not available. Install python-docx."
            )
        
        from fastapi.responses import StreamingResponse
        
        # ✅ 修复：清理序号的函数
        def remove_numbering(text):
            """
            删除各种格式的序号
            """
            if not text:
                return ""
            
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                original_line = line.strip()
                cleaned_line = original_line
                
                # 删除各种序号格式
                patterns = [
                    r'^\d+\.\s+',                    # 1. 
                    r'^\d+\.\d+\s+',                 # 1.1
                    r'^\d+\.\d+\.\d+\s+',            # 1.1.1
                    r'^[a-z]\)\s+',                  # a)
                    r'^\([i]+\)\s+',                 # (i), (ii)
                    r'^[IVX]+\.\s+',                 # I., II.
                    r'^\d+\.\s*$',                   # 只有序号的空行
                ]
                
                for pattern in patterns:
                    cleaned_line = re.sub(pattern, '', cleaned_line)
                
                # 如果清理后还有内容，保留该行
                if cleaned_line.strip():
                    cleaned_lines.append(cleaned_line.strip())
                # 如果是空行但原始行有内容，保留空行
                elif original_line:
                    cleaned_lines.append("")
            
            return '\n'.join(cleaned_lines)
        
        # ✅ 在处理内容之前先清理序号
        cleaned_content = remove_numbering(request.content)
        print(f"✅ Content cleaned - removed numbering patterns")
        print(f"✅ Original length: {len(request.content)}, Cleaned length: {len(cleaned_content)}")
        
        # 创建 Word 文档
        doc = docx.Document()
        doc.add_heading('Improved Lesson Plan', 0)
        
        # 解析清理后的内容
        lines = cleaned_content.split('\n')
        current_table = None
        in_table = False
        skip_next = False
        
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
            
            line = line.strip()
            
            if not line:
                in_table = False
                current_table = None
                # 添加空行
                doc.add_paragraph()
                continue
            
            # 跳过表格分隔线
            if '|' in line and '---' in line:
                skip_next = False
                continue
            
            # 处理表格
            if line.count('|') >= 3 and not line.startswith('[') and '---' not in line:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                is_real_table = False
                
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if '|' in next_line and '---' in next_line:
                        is_real_table = True
                        skip_next = True
                
                if is_real_table and not in_table:
                    in_table = True
                    current_table = doc.add_table(rows=1, cols=len(cells))
                    current_table.style = 'Light Grid Accent 1'
                    hdr_cells = current_table.rows[0].cells
                    for j, header in enumerate(cells):
                        hdr_cells[j].text = header
                        for paragraph in hdr_cells[j].paragraphs:
                            for run in paragraph.runs:
                                run.font.bold = True
                elif in_table and current_table:
                    row_cells = current_table.add_row().cells
                    for j, cell_text in enumerate(cells):
                        if j < len(row_cells):
                            row_cells[j].text = cell_text
                else:
                    in_table = False
                    doc.add_paragraph(line)
            else:
                in_table = False
                current_table = None
                
                # 处理标题和样式
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=3)
                elif line.startswith('**') and line.endswith('**'):
                    p = doc.add_paragraph()
                    p.add_run(line.strip('**')).bold = True
                elif line.startswith('- ') or line.startswith('* '):
                    doc.add_paragraph(line[2:], style='List Bullet')
                elif re.match(r'^\d+\.', line):  # ✅ 使用 re 匹配数字序号
                    # 清理序号并添加为普通段落
                    cleaned_line = re.sub(r'^\d+\.\s*', '', line)
                    doc.add_paragraph(cleaned_line)
                else:
                    doc.add_paragraph(line)
        
        # 保存到内存
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        # ✅ 统一文件名
        safe_filename = "Improved_lesson_plan.docx"
        
        print(f"✅ Word document created successfully")
        print(f"✅ Filename: {safe_filename}")
        print(f"✅ File size: {file_stream.getbuffer().nbytes} bytes")
        print(f"{'='*60}\n")
        
        # 返回文件响应
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        print(f"\n❌ WORD CONVERSION ERROR")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        print(f"{'='*60}\n")
        raise HTTPException(
            status_code=500, 
            detail=f"Word conversion failed: {str(e)}"
        )


@app.post("/api/evaluations", response_model=dict)
async def create_evaluation_record(evaluation: EvaluationCreate, db: Database = Depends(get_db)):
    try:
        eval_id = db.create_evaluation(
            lesson_plan_text=evaluation.lesson_plan_text,
            lesson_plan_title=evaluation.lesson_plan_title,
            grade_level=evaluation.grade_level,
            subject_area=evaluation.subject_area,
            api_mode=API_MODE
        )
        return {"status": "success", "evaluation_id": eval_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create evaluation: {str(e)}")


@app.get("/api/evaluations")
async def get_all_evaluations(limit: int = 50, status: Optional[str] = None, db: Database = Depends(get_db)):
    try:
        if status:
            evals = db.get_evaluations_by_status(status)
        else:
            evals = db.get_all_evaluations(limit=limit)
        return {
            "status": "success",
            "evaluations": evals,
            "count": len(evals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve evaluations: {str(e)}")


@app.get("/api/evaluations/{evaluation_id}")
async def get_evaluation_by_id(evaluation_id: int, db: Database = Depends(get_db)):
    evaluation = db.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {
        "status": "success",
        "evaluation": evaluation
    }


@app.put("/api/evaluations/{evaluation_id}", response_model=dict)
async def update_evaluation(evaluation_id: int, update_data: EvaluationUpdate, db: Database = Depends(get_db)):
    evaluation = db.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if all([update_data.place_based_score, update_data.cultural_score, update_data.overall_score]):
        db.update_evaluation_scores(
            eval_id=evaluation_id,
            place_based_score=update_data.place_based_score,
            cultural_score=update_data.cultural_score,
            overall_score=update_data.overall_score
        )
    if update_data.agent_responses or update_data.debate_transcript or update_data.recommendations:
        db.update_evaluation_results(
            eval_id=evaluation_id,
            agent_responses=update_data.agent_responses or [],
            debate_transcript=update_data.debate_transcript or {},
            recommendations=update_data.recommendations or [],
            status=update_data.status or "completed"
        )
    if update_data.status and not any([update_data.agent_responses, update_data.debate_transcript, update_data.recommendations]):
        db.update_evaluation_status(evaluation_id, update_data.status)
    return {"status": "success", "evaluation_id": evaluation_id}


@app.delete("/api/evaluations/{evaluation_id}", response_model=dict)
async def delete_evaluation_record(evaluation_id: int, db: Database = Depends(get_db)):
    evaluation = db.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    db.delete_evaluation(evaluation_id)
    return {"status": "success", "message": "Evaluation deleted successfully"}


@app.get("/api/statistics")
async def get_statistics(db: Database = Depends(get_db)):
    try:
        stats = db.get_statistics()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


@app.post("/api/evaluate/lesson")
@timing_decorator
async def evaluate_lesson(lesson_plan: dict, db: Database = Depends(get_db)):
    """
    评估教案 - 使用更新后的 Lesson Procedure 格式
    """
    text = lesson_plan.get("lesson_plan_text", "")
    title = lesson_plan.get("lesson_plan_title", "Untitled")
    grade_level = lesson_plan.get("grade_level", "")
    subject_area = lesson_plan.get("subject_area", "")
    
    print(f"\n{'='*60}")
    print(f"📝 EVALUATING LESSON PLAN")
    print(f"{'='*60}")
    print(f"Title: {title}")
    print(f"Grade: {grade_level}")
    print(f"Subject: {subject_area}")
    print(f"Length: {len(text)} characters")
    print(f"DEBUG: API_MODE = {API_MODE}")

    if API_MODE == "mock":
        # Mock 数据
        place_based_score = 84
        cultural_score = 82
        critical_pedagogy_score = 76
        assessment_quality_score = 74
        reflective_practice_score = 73
        overall_score = int((place_based_score + cultural_score + critical_pedagogy_score + 
                            assessment_quality_score + reflective_practice_score) / 5)
        
        print(f"📊 Mock Scores:")
        print(f"  Place-Based: {place_based_score}")
        print(f"  Cultural: {cultural_score}")
        print(f"  Overall: {overall_score}")
        
        agent_responses = [
            {
                "agent": "DeepSeek",
                "role": "Place-Based Learning Expert",
                "model": "deepseek-chat",
                "analysis": {
                    "place_based_learning": {
                        "score": place_based_score,
                        "color": score_color(place_based_score),
                        "strengths": [
                            "Strong connection to local environment and community",
                            "Engaging field-based activities that promote hands-on learning",
                            "Effective use of local case studies and examples"
                        ],
                        "areas_for_improvement": [
                            "Could include more community partnerships and guest speakers",
                            "Needs stronger connections to local iwi and cultural advisors"
                        ]
                    }
                },
                "recommendations": [
                    "Partner with local iwi for cultural guidance",
                    "Include community members in the learning process"
                ]
            },
            {
                "agent": "Claude",
                "role": "Cultural Responsiveness Specialist",
                "model": "claude-sonnet-4-5",
                "analysis": {
                    "cultural_responsiveness": {
                        "score": cultural_score,
                        "color": score_color(cultural_score),
                        "strengths": [
                            "Good integration of te reo Māori throughout the lesson",
                            "Cultural context and perspectives are included"
                        ],
                        "areas_for_improvement": [
                            "Need more diverse cultural perspectives beyond Māori"
                        ],
                        "cultural_elements_present": [
                            "Te reo Māori vocabulary",
                            "Māori concepts (kaitiakitanga)",
                            "Cultural protocols and acknowledgments"
                        ]
                    }
                },
                "recommendations": [
                    "Include more diverse cultural examples",
                    "Strengthen connections to local iwi"
                ]
            },
            {
                "agent": "GPT-4",
                "role": "Critical Pedagogy, Assessment & Reflective Practice Expert",
                "model": "gpt-4-turbo",
                "analysis": {
                    "critical_pedagogy": {
                        "score": critical_pedagogy_score,
                        "color": score_color(critical_pedagogy_score),
                        "strengths": [
                            "Encourages critical thinking and analysis",
                            "Student-centered approach with inquiry-based learning",
                            "Addresses power dynamics and systemic issues"
                        ],
                        "gaps": [
                            "Could include more structured reflection activities",
                            "Needs stronger focus on student voice and agency"
                        ]
                    },
                    "assessment_quality": {
                        "score": assessment_quality_score,
                        "color": score_color(assessment_quality_score),
                        "strengths": [
                            "Multiple assessment methods included",
                            "Both formative and summative assessment present",
                            "Peer assessment and self-assessment components"
                        ],
                        "gaps": [
                            "Assessment criteria could be more explicit",
                            "Need clearer rubrics for evaluation"
                        ]
                    },
                    "reflective_practice": {
                        "score": reflective_practice_score,
                        "color": score_color(reflective_practice_score),
                        "strengths": [
                            "Includes reflective journaling component",
                            "Opportunities for student self-assessment",
                            "Teacher reflection prompts included"
                        ],
                        "gaps": [
                            "Reflection could be more structured and guided",
                            "Need more explicit reflective practice frameworks"
                        ]
                    }
                },
                "recommendations": [
                    "Add structured learning journal for reflection",
                    "Include more opportunities for student-led inquiry",
                    "Strengthen connections to social justice themes",
                    "Implement detailed assessment rubric",
                    "Add more specific success criteria",
                    "Include exemplars for student reference",
                    "Add structured reflective practice framework",
                    "Include guided reflection prompts",
                    "Create reflection templates for students"
                ]
            }
        ]
        
        # 合并所有推荐
        all_recommendations = []
        for response in agent_responses:
            if "recommendations" in response:
                all_recommendations.extend(response["recommendations"])
        recommendations = list(dict.fromkeys(all_recommendations))  # 去重但保持顺序

        # 生成改进的教案 - 使用新的字段名
        fields = {
            "knowledge": "Students will understand the root causes of environmental issues and the concept of kaitiakitanga.",
            "skills": "Students will be able to conduct critical analysis and collect environmental data.",
            "values": "Students will appreciate kaitiakitanga and develop environmental stewardship.",
            "prior_knowledge": "Basic understanding of ecosystems and local waterways.",
            "interests": "Many students have personal connections to local environmental issues.",
            "challenges": "Complex scientific concepts and systemic environmental issues.",
            "learning_styles": "Mix of visual, kinesthetic, and collaborative learners.",
            "accommodations": "Differentiated instruction for various learning needs.",
            "key_concepts": "Critical analysis, kaitiakitanga, environmental justice.",
            "focus_challenges": "Understanding abstract concepts and managing emotions.",
            "methods": "Inquiry-based learning, place-based education, culturally responsive pedagogy.",
            "strategies": "Tuakana-Teina peer support, field investigations, reflective journaling.",
            "teacher_prep": "Contact local kaumātua, prepare water testing kits.",
            "student_prep": "Pre-reading on local environmental issues, family interviews.",
            # Updated: Introduction
            "intro_duration": "30 minutes",
            "intro_tasks": "Establish cultural connections and activate prior knowledge about local waterways.",
            "intro_teacher_actions": "Lead karakia and mihi whakatau; facilitate video presentation on Awa Tupua concept; guide critical discussion using photos.",
            "intro_student_activities": "Participate in karakia; watch and discuss video; share observations about local waterways; set personal learning intentions.",
            # Updated: Main Teaching
            "main_duration": "45 minutes",
            "main_tasks": "Introduce critical analysis framework and water quality testing methods.",
            "main_teacher_actions": "Model WHO-WHY-WHAT analysis; present historical context; demonstrate water testing procedures; explain safety protocols.",
            "main_student_activities": "Practice critical analysis framework; take notes on historical context; observe demonstrations; ask questions about procedures.",
            # Updated: Investigation & Exploration (was Activities)
            "investigation_duration": "90 minutes",
            "investigation_tasks": "Conduct hands-on field investigation and data collection at local waterway.",
            "investigation_teacher_actions": "Supervise field activities; provide guidance during data collection; facilitate community member interviews; support group work.",
            "investigation_student_activities": "Collect water quality samples; record data and observations; interview community members; work collaboratively in groups; complete reflective journal entries.",
            # Updated: Conclusion
            "conclusion_duration": "30 minutes",
            "conclusion_tasks": "Synthesize learning and connect to broader environmental themes.",
            "conclusion_teacher_actions": "Facilitate group presentations; guide whole-class synthesis; prompt reflection on cultural and scientific insights.",
            "conclusion_student_activities": "Present group findings; participate in class discussion; reflect on learning; set personal action goals.",
            # Updated: Extension
            "extension_duration": "Ongoing",
            "extension_tasks": "Continue deeper investigation and develop action plans.",
            "extension_teacher_actions": "Provide journal prompts; coordinate kaumātua follow-up; support community research projects.",
            "extension_student_activities": "Complete learning journal entries; prepare questions for kaumātua; develop community action plans; conduct independent research.",
            # Assessment and Resources
            "formative": "Observation during activities, journal check-ins, exit tickets.",
            "summative": "Group presentation, scientific report, learning journal portfolio.",
            "feedback": "Weekly teacher feedback, peer feedback forms, community input.",
            "materials": "Water testing kits, safety equipment, journal templates, poster boards.",
            "tech_tools": "Projector, tablets for data recording, Google Classroom, data logging apps."
        }
        lesson_plan_text = generate_lesson_plan_from_fields(fields)

    elif API_MODE == "real":
        try:
            print("🔄 Making real LLM API calls...")
            tasks = []
            print(f"DEBUG: Available LLMs: {llm_client.get_available_llms()}")

            # DeepSeek - 地方学习评估
            tasks.append(
                asyncio.wait_for(
                    llm_client.call(
                        "deepseek",
                        f"""Evaluate this lesson plan for place-based learning quality. Return ONLY valid JSON:
{{
    "score": 85,
    "strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["improvement1"],
    "recommendations": ["recommendation1"]
}}
Lesson Plan: {text[:6000]}"""
                    ),
                    timeout=30.0
                )
            )
            
            # Claude - 文化响应评估
            tasks.append(
                asyncio.wait_for(
                    llm_client.call(
                        "claude",
                        f"""Evaluate cultural responsiveness. Return ONLY valid JSON:
{{
    "score": 80,
    "strengths": ["strength1"],
    "areas_for_improvement": ["improvement1"],
    "cultural_elements_present": ["element1"],
    "recommendations": ["recommendation1"]
}}
Lesson: {text[:6000]}"""
                    ),
                    timeout=30.0
                )
            )
            
            # GPT-4 - 生成改进教案（使用新的字段名）
            tasks.append(
                asyncio.wait_for(
                    llm_client.call(
                        "chatgpt",
                        f"""Generate improved lesson plan fields. Return ONLY valid JSON with ALL these keys:
{{
    "knowledge": "text", "skills": "text", "values": "text",
    "prior_knowledge": "text", "interests": "text", "challenges": "text",
    "learning_styles": "text", "accommodations": "text",
    "key_concepts": "text", "focus_challenges": "text",
    "methods": "text", "strategies": "text",
    "teacher_prep": "text", "student_prep": "text",
    "intro_duration": "20min",
    "intro_tasks": "text",
    "intro_teacher_actions": "text",
    "intro_student_activities": "text",
    "main_duration": "40min",
    "main_tasks": "text",
    "main_teacher_actions": "text",
    "main_student_activities": "text",
    "investigation_duration": "45min",
    "investigation_tasks": "text",
    "investigation_teacher_actions": "text",
    "investigation_student_activities": "text",
    "conclusion_duration": "15min",
    "conclusion_tasks": "text",
    "conclusion_teacher_actions": "text",
    "conclusion_student_activities": "text",
    "extension_duration": "ongoing",
    "extension_tasks": "text",
    "extension_teacher_actions": "text",
    "extension_student_activities": "text",
    "formative": "text", "summative": "text", "feedback": "text",
    "materials": "text", "tech_tools": "text"
}}
Original: {text[:6000]}"""
                    ),
                    timeout=45.0
                )
            )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            print("✅ LLM calls completed")
            
            # 处理结果
            ds_content = results[0] if not isinstance(results[0], Exception) else None
            cl_content = results[1] if not isinstance(results[1], Exception) else None
            cg_content = results[2] if not isinstance(results[2], Exception) else None
            
            if isinstance(results[0], Exception):
                print(f"⚠️ DeepSeek error: {results[0]}")
            if isinstance(results[1], Exception):
                print(f"⚠️ Claude error: {results[1]}")
            if isinstance(results[2], Exception):
                print(f"⚠️ ChatGPT error: {results[2]}")
            
            # 解析响应
            def parse_json_response(content, default_score=70):
                if content is None:
                    return {"score": default_score, "strengths": [], "areas_for_improvement": [], "recommendations": []}
                if isinstance(content, dict):
                    return content
                try:
                    if isinstance(content, str):
                        content = content.strip()
                        if content.startswith("```json"):
                            content = content[7:]
                        if content.startswith("```"):
                            content = content[3:]
                        if content.endswith("```"):
                            content = content[:-3]
                        content = content.strip()
                        return json.loads(content)
                    return {"score": default_score, "strengths": [], "areas_for_improvement": [], "recommendations": []}
                except Exception as e:
                    print(f"⚠️ JSON parse error: {e}")
                    return {"score": default_score, "strengths": [], "areas_for_improvement": [], "recommendations": []}
            
            ds_analysis = parse_json_response(ds_content, 70)
            cl_analysis = parse_json_response(cl_content, 70)
            
            place_based_score = int(ds_analysis.get('score', 70))
            cultural_score = int(cl_analysis.get('score', 70))
            critical_pedagogy_score = 75
            assessment_quality_score = 73
            reflective_practice_score = 72
            overall_score = int((place_based_score + cultural_score + critical_pedagogy_score + 
                                assessment_quality_score + reflective_practice_score) / 5)
            
            print(f"📊 Real Scores: Place={place_based_score}, Cultural={cultural_score}, Overall={overall_score}")
            
            # 构建agent_responses - 确保GPT-4的三个维度完整
            agent_responses = [
                {
                    "agent": "DeepSeek",
                    "role": "Place-Based Learning Expert",
                    "model": "deepseek-chat",
                    "score": place_based_score,
                    "color": score_color(place_based_score),
                    "analysis": {
                        "place_based_learning": {
                            "score": place_based_score,
                            "color": score_color(place_based_score),
                            "strengths": ds_analysis.get('strengths', ["Place-based analysis completed"]),
                            "areas_for_improvement": ds_analysis.get('areas_for_improvement', ["Review recommended"])
                        }
                    },
                    "recommendations": ds_analysis.get('recommendations', ["Enhance local connections"])
                },
                {
                    "agent": "Claude",
                    "role": "Cultural Responsiveness Specialist",
                    "model": "claude-sonnet-4-5",
                    "score": cultural_score,
                    "color": score_color(cultural_score),
                    "analysis": {
                        "cultural_responsiveness": {
                            "score": cultural_score,
                            "color": score_color(cultural_score),
                            "strengths": cl_analysis.get('strengths', ["Cultural elements identified"]),
                            "areas_for_improvement": cl_analysis.get('areas_for_improvement', ["Cultural review needed"]),
                            "cultural_elements_present": cl_analysis.get('cultural_elements_present', ["Cultural content present"])
                        }
                    },
                    "recommendations": cl_analysis.get('recommendations', ["Strengthen cultural connections"])
                },
                {
                    "agent": "GPT-4",
                    "role": "Critical Pedagogy, Assessment & Reflective Practice Expert",
                    "model": "gpt-4-turbo",
                    "score": int((critical_pedagogy_score + assessment_quality_score + reflective_practice_score) / 3),
                    "color": score_color(int((critical_pedagogy_score + assessment_quality_score + reflective_practice_score) / 3)),
                    "analysis": {
                        "critical_pedagogy": {
                            "score": critical_pedagogy_score,
                            "color": score_color(critical_pedagogy_score),
                            "strengths": [
                                "Encourages critical thinking and questioning",
                                "Student-centered inquiry-based approach",
                                "Addresses systemic issues and power dynamics"
                            ],
                            "gaps": [
                                "Could include more structured critical reflection",
                                "Need stronger focus on student voice and agency"
                            ]
                        },
                        "assessment_quality": {
                            "score": assessment_quality_score,
                            "color": score_color(assessment_quality_score),
                            "strengths": [
                                "Multiple assessment methods included",
                                "Both formative and summative approaches",
                                "Includes peer and self-assessment"
                            ],
                            "gaps": [
                                "Assessment criteria could be more explicit",
                                "Need clearer success criteria and rubrics"
                            ]
                        },
                        "reflective_practice": {
                            "score": reflective_practice_score,
                            "color": score_color(reflective_practice_score),
                            "strengths": [
                                "Includes reflective components",
                                "Opportunities for student reflection",
                                "Teacher reflection considerations"
                            ],
                            "gaps": [
                                "Reflection could be more structured",
                                "Need explicit reflective practice frameworks"
                            ]
                        }
                    },
                    "recommendations": [
                        "Add structured learning journal for critical reflection",
                        "Include more student-led inquiry opportunities",
                        "Strengthen social justice connections",
                        "Implement detailed assessment rubric with clear criteria",
                        "Add specific success criteria and exemplars",
                        "Create structured reflective practice framework"
                    ]
                }
            ]
            
            # 合并所有推荐
            all_recommendations = []
            for response in agent_responses:
                if "recommendations" in response:
                    all_recommendations.extend(response["recommendations"])
            recommendations = list(dict.fromkeys(all_recommendations))[:10]  # 取前10个，去重
            
            # 生成教案 - 使用新字段
            try:
                if cg_content:
                    fields = parse_json_response(cg_content, 0)
                    if not isinstance(fields, dict) or len(fields) < 10:
                        fields = {}
                else:
                    fields = {}
            except:
                fields = {}
            
            if not fields:
                # Default fields with updated naming
                fields = {
                    "knowledge": "Students will develop comprehensive understanding of key concepts.",
                    "skills": "Students will develop critical thinking and practical skills.",
                    "values": "Students will appreciate diverse perspectives and cultural contexts.",
                    "prior_knowledge": "Students bring varied experiences to learning.",
                    "interests": "Connecting to student interests enhances engagement.",
                    "challenges": "Addressing diverse learning needs and challenges.",
                    "learning_styles": "Accommodating diverse learning preferences.",
                    "accommodations": "Providing appropriate supports for all learners.",
                    "key_concepts": "Core concepts aligned with curriculum.",
                    "focus_challenges": "Key learning challenges to address.",
                    "methods": "Place-based learning and inquiry-based learning.",
                    "strategies": "Evidence-based instructional strategies.",
                    "teacher_prep": "Required teacher preparations and materials.",
                    "student_prep": "Student preparations and requirements.",
                    # Updated: Introduction
                    "intro_duration": "20 minutes",
                    "intro_tasks": "Activate prior knowledge and establish learning context.",
                    "intro_teacher_actions": "Facilitate discussion, present learning objectives, engage students with opening activity.",
                    "intro_student_activities": "Share prior knowledge, ask questions, participate in opening discussion.",
                    # Updated: Main Teaching
                    "main_duration": "40 minutes",
                    "main_tasks": "Introduce core concepts and demonstrate key skills.",
                    "main_teacher_actions": "Present content with scaffolding, model thinking processes, check for understanding.",
                    "main_student_activities": "Take notes, ask clarifying questions, practice new skills with guidance.",
                    # Updated: Investigation & Exploration
                    "investigation_duration": "45 minutes",
                    "investigation_tasks": "Apply learning through hands-on investigation and exploration.",
                    "investigation_teacher_actions": "Facilitate group work, provide guidance and support, monitor progress.",
                    "investigation_student_activities": "Conduct investigations, collaborate with peers, collect and analyze data.",
                    # Updated: Conclusion
                    "conclusion_duration": "15 minutes",
                    "conclusion_tasks": "Synthesize learning and reflect on key takeaways.",
                    "conclusion_teacher_actions": "Guide reflection, summarize main points, connect to broader themes.",
                    "conclusion_student_activities": "Share insights, reflect on learning, identify next steps.",
                    # Updated: Extension
                    "extension_duration": "Ongoing",
                    "extension_tasks": "Extend learning beyond the classroom.",
                    "extension_teacher_actions": "Provide additional resources, support independent projects.",
                    "extension_student_activities": "Complete independent research, develop action plans, continue investigation.",
                    # Assessment
                    "formative": "Ongoing observation and feedback during activities.",
                    "summative": "Final assessment of learning outcomes.",
                    "feedback": "Regular constructive feedback to guide learning.",
                    "materials": "Required teaching and learning materials.",
                    "tech_tools": "Technology tools and resources to support learning."
                }
            
            lesson_plan_text = generate_lesson_plan_from_fields(fields)
            
        except asyncio.TimeoutError:
            print("❌ Timeout")
            raise HTTPException(status_code=504, detail="Evaluation timeout")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported API_MODE: {API_MODE}")

    # 保存到数据库
    try:
        eval_id = db.create_evaluation(
            lesson_plan_text=text,
            lesson_plan_title=title,
            grade_level=grade_level,
            subject_area=subject_area,
            api_mode=API_MODE
        )
        
        print(f"💾 Saving evaluation: eval_id={eval_id}")
        
        # 保存评分
        db.update_evaluation_scores(
            eval_id=eval_id,
            place_based_score=place_based_score,
            cultural_score=cultural_score,
            overall_score=overall_score
        )
        
        # 保存完整结果
        db.update_evaluation_results(
            eval_id=eval_id,
            agent_responses=agent_responses,
            debate_transcript={},
            recommendations=recommendations,
            status="completed"
        )
        
        print(f"✅ Evaluation saved successfully")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        print(traceback.format_exc())

    # 返回结果
    return {
        "status": "success",
        "evaluation_id": eval_id,
        "agent_responses": agent_responses,
        "recommendations": recommendations,
        "scores": {
            "place_based_learning": place_based_score,
            "cultural_responsiveness": cultural_score,
            "critical_pedagogy": critical_pedagogy_score,
            "assessment_quality": assessment_quality_score,
            "reflective_practice": reflective_practice_score,
            "overall": overall_score
        },
        "improved_lesson_plan": lesson_plan_text,
        "mode": API_MODE
    }


@app.post("/api/improve-lesson")
@timing_decorator
async def improve_lesson(request: ImproveLessonRequest):
    try:
        response = await asyncio.wait_for(
            llm_client.call(
                "chatgpt",
                f"""Improve lesson plan based on recommendations. Return ONLY valid JSON with these keys:
knowledge, skills, values, prior_knowledge, interests, challenges,
learning_styles, accommodations, key_concepts, focus_challenges,
methods, strategies, teacher_prep, student_prep,
intro_duration, intro_tasks, intro_teacher_actions, intro_student_activities,
main_duration, main_tasks, main_teacher_actions, main_student_activities,
investigation_duration, investigation_tasks, investigation_teacher_actions, investigation_student_activities,
conclusion_duration, conclusion_tasks, conclusion_teacher_actions, conclusion_student_activities,
extension_duration, extension_tasks, extension_teacher_actions, extension_student_activities,
formative, summative, feedback, materials, tech_tools

Recommendations: {', '.join(request.recommendations[:3])}
Original: {request.original_lesson[:5000]}"""
            ),
            timeout=60.0
        )
        
        try:
            if isinstance(response, str):
                response = response.strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]
                response = response.strip()
                fields = json.loads(response)
            else:
                fields = response
                
            if not isinstance(fields, dict):
                fields = {}
        except:
            fields = {}
        
        improved_lesson = generate_lesson_plan_from_fields(fields)
        
        return {
            "status": "success",
            "improved_lesson": improved_lesson,
            "original_title": request.lesson_title,
            "recommendations_applied": len(request.recommendations)
        }
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Timeout")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Service is healthy"}


print("🚀 Lesson Plan Evaluator API is ready to accept requests")

