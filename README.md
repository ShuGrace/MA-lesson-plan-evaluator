# Lesson Plan Evaluator API - Framework v3.0

> Multi-Agent AI System for Comprehensive Lesson Plan Evaluation in Aotearoa New Zealand Educational Context

[![Framework Version](https://img.shields.io/badge/Framework-v3.0-blue)](https://github.com/yourusername/lesson-evaluator)
[![Python](https://img.shields.io/badge/Python-3.9+-green)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-teal)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-61DAFB)](https://reactjs.org/)

---

## 🎯 Framework v3.0 Overview

### **Key Changes from v2.0**

#### **1. Dimensions (4 instead of 5)**
| Dimension | Weight | Agent | Changes |
|-----------|--------|-------|---------|
| **Place-Based Learning** | 25% | DeepSeek | *No change* |
| **Cultural Responsiveness & Māori Perspectives** | 35% | Claude | ✅ **FULLY INTEGRATED** (was 2 separate dimensions) |
| **Critical Pedagogy** | 25% | GPT-Critical | *No change* |
| **Lesson Design Quality** | 15% | GPT-Design | ✅ **NEW DIMENSION** |

#### **2. Agents (4)**
1. **DeepSeek** - Place-based Learning Specialist
   - Evaluates local context integration, community engagement
   - Model: `deepseek-chat`
   
2. **Claude** - Cultural Responsiveness & Māori Perspectives Specialist *(INTEGRATED)*
   - Unified evaluation of general cultural responsiveness AND Māori perspectives
   - No longer separated into two sections
   - Model: `claude-sonnet-4-20250514`
   
3. **GPT-Critical** - Critical Pedagogy & Student Engagement Specialist
   - Evaluates power structures, student agency, social justice
   - Model: `gpt-4o`
   
4. **GPT-Design** - Lesson Design & Quality Specialist *(NEW)*
   - Evaluates instructional design, assessment alignment, differentiation
   - Model: `gpt-4o`

#### **3. Architecture Improvements**
- ✅ API enable/disable switches (`ENABLE_DEEPSEEK`, `ENABLE_CLAUDE`, `ENABLE_GPT`)
- ✅ Enhanced retry logic with exponential backoff
- ✅ Dynamic weight normalization when APIs are disabled
- ✅ Improved error handling and logging
- ✅ Backward compatibility with v2.0 data

---

## 📊 Theoretical Framework

### **Dimensions Detail**

#### **1. Place-Based Learning (25%)**
- **Indicators (6):** PBL-01 to PBL-06
- **Key Focus:**
  - Local context integration with specific named places
  - Community partnerships and engagement
  - Authentic real-world problem-solving
  - Interdisciplinary integration
  - Indigenous knowledge systems
  - Critical place consciousness

#### **2. Cultural Responsiveness & Māori Perspectives - INTEGRATED (35%)**
- **Indicators (10):** CRMP-01 to CRMP-10
- **Key Focus:**
  - Cultural knowledge validation
  - Te Reo Māori integration
  - Mātauranga Māori & multicultural content
  - Culturally responsive pedagogy
  - Tikanga and cultural protocols
  - Māori worldview representation
  - Te Tiriti partnership principles
  - High expectations with cultural scaffolding
  - Critical consciousness & decolonization
  - Cultural sustaining & Te Reo revitalization

*Note: This is a unified dimension that simultaneously addresses both general cultural responsiveness AND Māori perspectives, reflecting Aotearoa New Zealand's bicultural educational context.*

#### **3. Critical Pedagogy & Student Engagement (25%)**
- **Indicators (8):** CP-01 to CP-08
- **Key Focus:**
  - Power structure analysis
  - Questioning dominant narratives
  - Student agency and voice
  - Dialogic teaching & collaboration
  - Lived experience centering
  - Social justice orientation
  - Praxis and action orientation
  - Critical reflexivity

#### **4. Lesson Design Quality (15%) - NEW**
- **Indicators (7):** LDQ-01 to LDQ-07
- **Key Focus:**
  - Clear learning objectives
  - Instructional coherence and flow
  - Assessment alignment and quality
  - Differentiation and scaffolding
  - Resource quality and appropriateness
  - Time allocation and pacing
  - Clarity and usability

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.9+
- Node.js 16+
- API Keys for:
  - OpenAI (GPT-4o)
  - Anthropic (Claude)
  - DeepSeek (optional)

### **Installation**

#### **1. Clone Repository**
```bash
git clone https://github.com/yourusername/lesson-evaluator.git
cd lesson-evaluator\backend

# Create virtual environment
python -m venv venv

# Open virtual environment
(VE is in backend, so you need go to backend and then carry on the code to open VE)
source venv/bin/activate  # On Windows: venv\Scripts\activate
.\.venv\Scripts\activate    # powershell

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env.development
# Edit .env.development with your API keys

# Run backend
python -m uvicorn app.main:app --reload --port 8000

cd frontend

# Install dependencies
npm install

# Start development server
npm run dev



# .env
# API Mode
API_MODE=real  # or "mock" for testing

# API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here

# Framework v3.0: API Switches
ENABLE_DEEPSEEK=true
ENABLE_CLAUDE=true
ENABLE_GPT=true

# API Configuration
API_TIMEOUT=180
API_MAX_RETRIES=5
API_RETRY_DELAY=15
CONTINUE_ON_API_FAILURE=true

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=false



# API control

# Example: Disable DeepSeek if out of credit
ENABLE_DEEPSEEK=false
ENABLE_CLAUDE=true
ENABLE_GPT=true



# Project Structure

lesson-evaluator/
├── backend/
│   ├── app/
│   │   ├── config.py                 # ✅ v3.0 updated
│   │   ├── db/
│   │   │   └── database.py
│   │   ├── services/
│   │   │   ├── llm_client.py         # ✅ v3.0 updated
│   │   │   └── framework_loader.py   # ✅ v3.0 updated
│   │   └── utils/
│   │       └── evaluation_helpers.py # ✅ v3.0 updated
│   ├── framework/                    # ✅ v3.0 structure
│   │   ├── theoretical_framework.json # ✅ v3.0
│   │   ├── agent_design.json          # ✅ v3.0
│   │   └── composite_scoring_rubric.txt # ✅ v3.0
│   ├── prompts/
│   │   ├── deepseek_place_based.txt
│   │   ├── claude_cultural_integrated.txt # ✅ v3.0 updated
│   │   ├── gpt_critical_pedagogy.txt
│   │   └── gpt_lesson_design.txt          # ✅ v3.0 new
│   ├── main.py                       # ✅ v3.0 updated
│   ├── requirements.txt
│   ├── .env.development              # ✅ v3.0 updated
│   └── .env.production               # ✅ v3.0 updated
├── frontend/
│   ├── src/
│   │   ├── App.jsx                   # ✅ v3.0 updated
│   │   └── App.css
│   └── package.json
└── README.md                         # ✅ v3.0 updated
```


# System Architecture

Multi-Agent Lesson Plan Evaluator - Framework v3.0

Overview
Full-stack web app for evaluating lesson plans using 4 specialized AI agents.

Tech Stack
Code
React Frontend (Port 3000) 
    ↓ API calls
FastAPI Backend (Port 8000)
    ↓ Parallel requests
4 AI Agents → 3 LLM Providers
    ↓ Results
SQLite/PostgreSQL Database
Backend (Python)
Framework: FastAPI + Uvicorn
Database: SQLite (dev) / PostgreSQL (prod)
Deployment: Gunicorn on Railway
Key Services:
llm_client.py - API client for 3 LLMs
framework_loader.py - Load evaluation framework
evaluation_helpers.py - Score aggregation
Frontend (React)
Stack: React 19 + Vite 7
UI: lucide-react icons
Dev Server: Port 3000, proxies to backend 8000
Entry: App.jsx
4 AI Agents
DeepSeek - Place-Based Learning (25%)
Claude Sonnet 4 - Cultural Responsiveness & Māori Perspectives (35%)
GPT-4o (Critical) - Critical Pedagogy (25%)
GPT-4o (Design) - Lesson Design Quality (15%)
Data Flow
Code
User submits lesson plan 
  → FastAPI receives request
  → Calls 4 LLMs in parallel
  → Each returns dimension score (1-5)
  → Weighted aggregation
  → Returns JSON result
Key Features
Resilient: Continues on API failure, dynamic weight normalization
Flexible: Mock/real API modes, individual API on/off switches
Reliable: Exponential backoff retry (max 5 attempts)