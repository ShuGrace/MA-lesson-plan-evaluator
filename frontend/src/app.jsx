import React, { useState, useEffect, useRef } from 'react';
import { Send, BookOpen, TrendingUp, Users, Globe, FileText, AlertCircle, CheckCircle, Loader, Database, History, Target, Brain, ClipboardCheck, MessageCircle, Upload, FileCheck, X, Download, Sparkles, Lightbulb } from 'lucide-react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

// ✅ 新西兰教育相关推荐网站列表
const RECOMMENDED_WEBSITES = {
  maori_language: [
    { url: 'https://maoridictionary.co.nz', name: 'Te Aka Māori Dictionary' },
    { url: 'https://tereomaori.tki.org.nz', name: 'Te Reo Māori - TKI' },
    { url: 'https://tematawai.maori.nz', name: 'Te Mātāwai' }
  ],
  cultural: [
    { url: 'https://teara.govt.nz', name: 'Te Ara - Encyclopedia of NZ' },
    { url: 'https://nzhistory.govt.nz', name: 'NZ History' },
    { url: 'https://aucklandmuseum.com', name: 'Auckland Museum' }
  ],
  curriculum: [
    { url: 'https://nzcurriculum.tki.org.nz', name: 'NZ Curriculum Online' },
    { url: 'https://tki.org.nz', name: 'TKI - Te Kete Ipurangi' },
    { url: 'https://education.govt.nz', name: 'Ministry of Education' }
  ],
  science: [
    { url: 'https://sciencelearn.org.nz', name: 'Science Learning Hub' },
    { url: 'https://scienceonline.tki.org.nz', name: 'Science Online' }
  ],
  mathematics: [
    { url: 'https://nzmaths.co.nz', name: 'NZ Maths' }
  ],
  literacy: [
    { url: 'https://englishonline.tki.org.nz', name: 'English Online' },
    { url: 'https://literacyonline.tki.org.nz', name: 'Literacy Online' }
  ],
  arts: [
    { url: 'https://artsonline.tki.org.nz', name: 'Arts Online' }
  ],
  assessment: [
    { url: 'https://nzqa.govt.nz', name: 'NZQA' },
    { url: 'https://ero.govt.nz', name: 'ERO' }
  ],
  professional: [
    { url: 'https://teachingcouncil.nz', name: 'Teaching Council NZ' },
    { url: 'https://nzcer.org.nz', name: 'NZCER' }
  ],
  sustainability: [
    { url: 'https://enviroschools.org.nz', name: 'Enviroschools' },
    { url: 'https://sustainability.tki.org.nz', name: 'Sustainability - TKI' }
  ]
};

// ✅ 根据agent分析维度选择相关网站（最多3个）
const getRelevantWebsites = (dimensionKey, subjectArea) => {
  const websites = [];
  
  if (dimensionKey === 'place_based_learning') {
    websites.push(...RECOMMENDED_WEBSITES.cultural);
    if (subjectArea?.toLowerCase().includes('science')) {
      websites.push(...RECOMMENDED_WEBSITES.science);
    }
    websites.push(...RECOMMENDED_WEBSITES.sustainability);
  } else if (dimensionKey === 'cultural_responsiveness') {
    websites.push(...RECOMMENDED_WEBSITES.maori_language);
    websites.push(...RECOMMENDED_WEBSITES.cultural);
  } else if (dimensionKey === 'critical_pedagogy') {
    websites.push(...RECOMMENDED_WEBSITES.curriculum);
    websites.push(...RECOMMENDED_WEBSITES.professional);
  } else if (dimensionKey === 'assessment_quality') {
    websites.push(...RECOMMENDED_WEBSITES.assessment);
    websites.push(...RECOMMENDED_WEBSITES.curriculum);
  } else if (dimensionKey === 'reflective_practice') {
    websites.push(...RECOMMENDED_WEBSITES.professional);
    websites.push(...RECOMMENDED_WEBSITES.curriculum);
  }
  
  // 去重并限制为最多3个
  const uniqueWebsites = Array.from(new Map(websites.map(w => [w.url, w])).values());
  return uniqueWebsites.slice(0, 3);
};

function App() {
  // 原有状态
  const [lessonTitle, setLessonTitle] = useState('');
  const [lessonContent, setLessonContent] = useState('');
  const [gradeLevel, setGradeLevel] = useState('');
  const [subjectArea, setSubjectArea] = useState('');
  
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [error, setError] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  
  const [savedEvaluations, setSavedEvaluations] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  // 新增状态 - 文件上传功能
  const [inputMode, setInputMode] = useState('text'); // 'text' or 'file'
  const [uploadedFile, setUploadedFile] = useState(null);
  const [extractedText, setExtractedText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const fileInputRef = useRef(null);

  // 新增状态 - AI改进教案功能 - ✅ 添加流式文本状态
  const [isGenerating, setIsGenerating] = useState(false);
  const [improvedLesson, setImprovedLesson] = useState(null);
  const [streamingText, setStreamingText] = useState(''); // ✅ 新增：流式显示文本
  const improvedLessonRef = useRef(null); // ✅ 新增：用于自动滚动

  // 切换输入模式时的处理
  const handleInputModeChange = (mode) => {
    setInputMode(mode);
    // 清除评估结果和错误
    setEvaluationResult(null);
    setError(null);
    setSaveStatus(null);
    setImprovedLesson(null);
    setStreamingText(''); // ✅ 清除流式文本
    // 如果切换到 text 模式，清除文件
    if (mode === 'text') {
      setUploadedFile(null);
      setExtractedText('');
    }
  };

  useEffect(() => {
    loadSavedEvaluations();
  }, []);

  // ✅ 新增：自动滚动到底部
  useEffect(() => {
    if (improvedLessonRef.current && streamingText) {
      improvedLessonRef.current.scrollTop = improvedLessonRef.current.scrollHeight;
    }
  }, [streamingText]);

  const loadSavedEvaluations = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/evaluations?limit=20`);
      if (response.ok) {
        const data = await response.json();
        setSavedEvaluations(data.evaluations || data);
      }
    } catch (err) {
      console.error('Failed to load saved evaluations:', err);
    }
  };

  // 文件上传相关函数
  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) {
      await processFile(file);
    }
  };

  const handleFileDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      await processFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const processFile = async (file) => {
    const validTypes = [
      'application/pdf', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'
    ];
    
    if (!validTypes.includes(file.type)) {
      setError('Only PDF and Word (.docx, .doc) files are supported');
      return;
    }
    
    setUploadedFile(file);
    setError(null);
    setIsExtracting(true);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      console.log('Uploading file:', file.name);
      
      const response = await fetch(`${API_BASE_URL}/api/extract-text`, {
        method: 'POST',
        body: formData,
      });
      
      console.log('Upload response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Extracted text length:', data.text?.length);
      
      setExtractedText(data.text);
      setLessonContent(data.text);
      
      if (data.metadata?.title) {
        setLessonTitle(data.metadata.title);
      }
      
      setError(null);
      console.log('✅ File processed successfully');
      
    } catch (err) {
      console.error('❌ File processing error:', err);
      
      let errorMessage = 'File processing failed';
      if (err.message.includes('Failed to fetch')) {
        errorMessage = '❌ Cannot connect to server. Please check backend is running.';
      } else {
        errorMessage = `❌ ${err.message}`;
      }
      
      setError(errorMessage);
      setUploadedFile(null);
      setExtractedText('');
      setLessonContent('');
    } finally {
      setIsExtracting(false);
    }
  };

  const clearUploadedFile = () => {
    setUploadedFile(null);
    setExtractedText('');
    if (inputMode === 'file') {
      setLessonContent('');
    }
  };

  // ✅ 修改：AI改进教案函数 - 支持流式显示
  const handleGenerateImprovedLesson = async () => {
    setIsGenerating(true);
    setError(null);
    setStreamingText(''); // ✅ 清空之前的流式文本
    setImprovedLesson(null); // ✅ 清空完整文本
    
    try {
      const allRecommendations = [];
      
      evaluationResult.agent_responses.forEach(agent => {
        if (agent.recommendations) {
          allRecommendations.push(...agent.recommendations);
        }
        
        if (agent.analysis) {
          Object.values(agent.analysis).forEach(dimension => {
            if (dimension.gaps) {
              allRecommendations.push(...dimension.gaps);
            }
            if (dimension.areas_for_improvement) {
              allRecommendations.push(...dimension.areas_for_improvement);
            }
          });
        }
      });
      
      const response = await fetch(`${API_BASE_URL}/api/improve-lesson`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_lesson: lessonContent,
          lesson_title: lessonTitle,
          grade_level: gradeLevel,
          subject_area: subjectArea,
          recommendations: allRecommendations,
          scores: evaluationResult.scores,
          remove_numbering: true //后端删除序号
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate improved lesson');
      }
      
      // ✅ 检查是否支持流式响应
      const contentType = response.headers.get('content-type');
      
      if (response.body && contentType && contentType.includes('text/event-stream')) {
        // ✅ 流式响应处理
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          fullText += chunk;
          setStreamingText(fullText); // ✅ 更新流式文本
        }
        
        setImprovedLesson(fullText); // ✅ 设置完整文本
      } else {
        // ✅ 普通JSON响应处理
        const data = await response.json();
        setImprovedLesson(data.improved_lesson);
        setStreamingText(data.improved_lesson);
      }
      
    } catch (err) {
      setError(`Failed to generate improved lesson plan: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleEvaluate = async () => {
    const contentToEvaluate = lessonContent;
    
    if (!lessonTitle.trim() || !contentToEvaluate.trim()) {
      setError('Please enter both lesson title and content');
      return;
    }

    // 清除之前的所有状态
    setIsEvaluating(true);
    setError(null);
    setEvaluationResult(null);
    setSaveStatus(null);
    setImprovedLesson(null);
    setStreamingText(''); // ✅ 清除流式文本

    try {
      console.log('Sending evaluation request...');
      console.log('API URL:', `${API_BASE_URL}/api/evaluate/lesson`);
      
      const evalResponse = await fetch(`${API_BASE_URL}/api/evaluate/lesson`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lesson_plan_text: contentToEvaluate,
          lesson_plan_title: lessonTitle,
          grade_level: gradeLevel,
          subject_area: subjectArea,
        }),
      });

      console.log('Response status:', evalResponse.status);

      if (!evalResponse.ok) {
        const errorText = await evalResponse.text();
        console.error('Response error:', errorText);
        throw new Error(`Evaluation failed (${evalResponse.status}): ${errorText}`);
      }

      const result = await evalResponse.json();
      console.log('Evaluation result:', result);
      setEvaluationResult(result);
      setSaveStatus({ type: 'success', message: 'Evaluation saved to database!' });
      loadSavedEvaluations();

    } catch (err) {
      console.error('Evaluation error:', err);
      let errorMessage = 'An error occurred during evaluation';
      
      if (err.message.includes('Failed to fetch')) {
        errorMessage = '❌ Cannot connect to server. Please check:\n1. Backend is running on http://localhost:8000\n2. Run: python -m uvicorn main:app --reload';
      } else {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setIsEvaluating(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'EXCELLENT';
    if (score >= 60) return 'GOOD';
    return 'NEEDS WORK';
  };

  // ✅ 处理评分卡片点击跳转（已去除闪烁动画）
  const handleScoreCardClick = (agentKey) => {
    console.log('Clicked score card:', agentKey);
    
    if (agentKey === 'overall') {
      // Overall Score点击后跳转到Evaluation Results顶部
      const resultsSection = document.querySelector('.results-section');
      if (resultsSection) {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } else {
      // 尝试跳转到对应的dimension section
      const dimensionSection = document.querySelector(`[data-dimension-key="${agentKey}"]`);
      console.log('Looking for dimension section with key:', agentKey);
      console.log('Found dimension section:', dimensionSection);
      
      if (dimensionSection) {
        dimensionSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        console.warn(`Dimension section not found for key: ${agentKey}`);
        // 显示所有可用的data-dimension-key
        const allSections = document.querySelectorAll('[data-dimension-key]');
        console.log('Available dimension sections:', Array.from(allSections).map(section => section.getAttribute('data-dimension-key')));
      }
    }
  };

  const renderScoreCards = () => {
    if (!evaluationResult || !evaluationResult.scores) return null;

    const scoreConfig = [
      {
        key: 'place_based_learning',
        label: 'Place-Based Learning',
        icon: <Globe size={24} />
      },
      {
        key: 'cultural_responsiveness',
        label: 'Cultural Responsiveness',
        icon: <Users size={24} />
      },
      {
        key: 'critical_pedagogy',
        label: 'Critical Pedagogy',
        icon: <Brain size={24} />
      },
      {
        key: 'assessment_quality',
        label: 'Assessment Quality',
        icon: <ClipboardCheck size={24} />
      },
      {
        key: 'reflective_practice',
        label: 'Reflective Practice',
        icon: <MessageCircle size={24} />
      }
    ];

    const validScores = scoreConfig.filter(config => {
      const score = evaluationResult.scores[config.key];
      return score !== undefined && score !== null && score > 0;
    });

    if (validScores.length === 0) return null;

    const scoreCards = validScores.map(config => {
      const score = evaluationResult.scores[config.key];

      return (
        <div 
          key={config.key} 
          className="score-card clickable"
          onClick={() => handleScoreCardClick(config.key)}
          title={`Click to view ${config.label} evaluation`}
        >
          <div className="score-header">
            {config.icon}
            <h3>{config.label}</h3>
          </div>
          <div className="circular-progress">
            <svg width="140" height="140">
              <circle
                cx="70"
                cy="70"
                r="60"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="12"
              />
              <circle
                cx="70"
                cy="70"
                r="60"
                fill="none"
                stroke={getScoreColor(score)}
                strokeWidth="12"
                strokeDasharray={`${2 * Math.PI * 60}`}
                strokeDashoffset={`${2 * Math.PI * 60 * (1 - score / 100)}`}
                strokeLinecap="round"
                transform="rotate(-90 70 70)"
              />
            </svg>
            <div className="score-value">{score}</div>
          </div>
          <div className="score-label" style={{ color: getScoreColor(score) }}>
            {getScoreLabel(score)}
          </div>
        </div>
      );
    });

    // ✅ 添加 Overall Score 卡片到最后
    if (evaluationResult.scores?.overall) {
      scoreCards.push(
        <div 
          key="overall" 
          className="overall-score clickable"
          onClick={() => handleScoreCardClick('overall')}
          title="Click to go back to Evaluation Results"
        >
          <div className="score-header">
            <Target size={24} />
            <h3>Overall Score</h3>
          </div>
          <div className="circular-progress">
            <svg width="140" height="140">
              <circle
                cx="70"
                cy="70"
                r="60"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="12"
              />
              <circle
                cx="70"
                cy="70"
                r="60"
                fill="none"
                stroke={getScoreColor(evaluationResult.scores.overall)}
                strokeWidth="12"
                strokeDasharray={`${2 * Math.PI * 60}`}
                strokeDashoffset={`${2 * Math.PI * 60 * (1 - evaluationResult.scores.overall / 100)}`}
                strokeLinecap="round"
                transform="rotate(-90 70 70)"
              />
            </svg>
            <div className="score-value">{evaluationResult.scores.overall}</div>
          </div>
          <div className="score-label" style={{ color: getScoreColor(evaluationResult.scores.overall) }}>
            {getScoreLabel(evaluationResult.scores.overall)}
          </div>
        </div>
      );
    }

    return scoreCards;
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <BookOpen size={32} />
            <h1>Lesson Plan Evaluator</h1>
          </div>
          <div className="header-actions">
            <button 
              className="history-button"
              onClick={() => setShowHistory(!showHistory)}
            >
              <History size={20} />
              <span>History</span>
              {savedEvaluations.length > 0 && (
                <span className="badge">{savedEvaluations.length}</span>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="main-content-centered">
        <div className="content-wrapper">
          {showHistory && (
            <div className="history-sidebar">
              <h3>
                <History size={24} />
                Evaluation History
              </h3>
              {savedEvaluations.length === 0 ? (
                <p className="no-history">No saved evaluations yet</p>
              ) : (
                <div className="history-list">
                  {savedEvaluations.map(evaluation => (
                    <div key={evaluation.id} className="history-item">
                      <div className="history-item-header">
                        <strong>{evaluation.lesson_plan_title || 'Untitled'}</strong>
                        <span className="status-badge status-completed">Completed</span>
                      </div>
                      <div className="history-item-meta">
                        {evaluation.grade_level && <span>Grade: {evaluation.grade_level}</span>}
                        {evaluation.subject_area && <span>Subject: {evaluation.subject_area}</span>}
                      </div>
                      <div className="history-item-date">
                        {new Date(evaluation.created_at).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="content-grid">
            <div className="input-section">
              <h2>Lesson Plan Input</h2>
              
              <div className="input-tabs">
                <button 
                  className={`tab-button ${inputMode === 'text' ? 'active' : ''}`}
                  onClick={() => handleInputModeChange('text')}
                >
                  <FileText size={20} />
                  Text Input
                </button>
                <button 
                  className={`tab-button ${inputMode === 'file' ? 'active' : ''}`}
                  onClick={() => handleInputModeChange('file')}
                >
                  <Upload size={20} />
                  File Upload
                </button>
              </div>
              
              {inputMode === 'text' ? (
                <>
                  <div className="form-group">
                    <label htmlFor="text-lesson-title">Lesson Title *</label>
                    <input
                      id="text-lesson-title"
                      type="text"
                      placeholder="e.g., Water Quality Investigation"
                      value={lessonTitle}
                      onChange={(e) => setLessonTitle(e.target.value)}
                      className="input-field"
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="text-grade-level">Grade Level</label>
                      <input
                        id="text-grade-level"
                        type="text"
                        placeholder="e.g., Year 7-8"
                        value={gradeLevel}
                        onChange={(e) => setGradeLevel(e.target.value)}
                        className="input-field"
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="text-subject-area">Subject Area</label>
                      <input
                        id="text-subject-area"
                        type="text"
                        placeholder="e.g., Science"
                        value={subjectArea}
                        onChange={(e) => setSubjectArea(e.target.value)}
                        className="input-field"
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="text-lesson-content">Lesson Plan Content *</label>
                    <textarea
                      id="text-lesson-content"
                      placeholder="Paste your complete lesson plan here..."
                      value={lessonContent}
                      onChange={(e) => setLessonContent(e.target.value)}
                      className="textarea-field"
                      rows={15}
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="form-group">
                    <label htmlFor="file-lesson-title">Lesson Title *</label>
                    <input
                      id="file-lesson-title"
                      type="text"
                      placeholder="e.g., Water Quality Investigation"
                      value={lessonTitle}
                      onChange={(e) => setLessonTitle(e.target.value)}
                      className="input-field"
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="file-grade-level">Grade Level</label>
                      <input
                        id="file-grade-level"
                        type="text"
                        placeholder="e.g., Year 7-8"
                        value={gradeLevel}
                        onChange={(e) => setGradeLevel(e.target.value)}
                        className="input-field"
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="file-subject-area">Subject Area</label>
                      <input
                        id="file-subject-area"
                        type="text"
                        placeholder="e.g., Science"
                        value={subjectArea}
                        onChange={(e) => setSubjectArea(e.target.value)}
                        className="input-field"
                      />
                    </div>
                  </div>

                  <div 
                    className={`file-drop-zone ${isDragging ? 'dragging' : ''} ${uploadedFile ? 'has-file' : ''}`}
                    onDrop={handleFileDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => !uploadedFile && fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.doc"
                      onChange={handleFileSelect}
                      style={{ display: 'none' }}
                    />
                    
                    {isExtracting ? (
                      <div className="upload-status">
                        <Loader className="spinning" size={48} />
                        <p>Extracting text from file...</p>
                      </div>
                    ) : uploadedFile ? (
                      <div className="file-info">
                        <FileCheck size={48} color="#10b981" />
                        <p className="filename">{uploadedFile.name}</p>
                        <p className="file-size">{(uploadedFile.size / 1024).toFixed(1)} KB</p>
                        <button 
                          className="remove-file-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            clearUploadedFile();
                          }}
                          
                        >
                          <X size={18} />
                          <span>Remove File</span>
                        </button>
                      </div>
                    ) : (
                      <>
                        <Upload size={48} />
                        <p>Drag and drop your lesson plan file here</p>
                        <p className="file-hint">or click to browse</p>
                        <p className="file-types">Supported: PDF, DOC, DOCX</p>
                      </>
                    )}
                  </div>

                  {extractedText && (
                    <div className="form-group">
                      <label htmlFor="extracted-content">
                        Extracted Content (Editable)
                      </label>
                      <textarea
                        id="extracted-content"
                        value={lessonContent}
                        onChange={(e) => setLessonContent(e.target.value)}
                        className="textarea-field"
                        rows={15}
                      />
                    </div>
                  )}
                </>
              )}

              <button
                onClick={handleEvaluate}
                disabled={isEvaluating}
                className="submit-button"
              >
                {isEvaluating ? (
                  <>
                    <Loader className="spinning" size={20} />
                    Evaluating...
                  </>
                ) : (
                  <>
                    <Send size={20} />
                    Evaluate Lesson Plan
                  </>
                )}
              </button>

              {error && (
                <div className="error-message">
                  <AlertCircle size={20} />
                  <span>{error}</span>
                </div>
              )}

              {saveStatus && saveStatus.type === 'success' && (
                <div className="success-message">
                  <CheckCircle size={20} />
                  <span>{saveStatus.message}</span>
                </div>
              )}
            </div>

            {evaluationResult && (
              <div className="results-section">
                <h2>Evaluation Results</h2>
                
                {/* ✅ 所有评分卡片（包括Overall Score）都在这个网格中 */}
                <div className="scores-grid">
                  {renderScoreCards()}
                </div>

                {/* Agent Evaluations */}
                {evaluationResult.agent_responses && evaluationResult.agent_responses.length > 0 && (
                  <div className="agent-evaluations-section">
                    <h3>🤖 Agent Evaluations</h3>
                    {evaluationResult.agent_responses.map((agent, index) => {
                      console.log(`Agent ${index} (${agent.agent}):`, JSON.stringify(agent, null, 2));
                      
                      // ✅ 根据agent的role或analysis中的维度来确定对应的key
                      let agentKey = '';
                      if (agent.analysis) {
                        const analysisKeys = Object.keys(agent.analysis);
                        if (analysisKeys.length > 0) {
                          agentKey = analysisKeys[0]; // 使用第一个analysis key作为标识
                        }
                      }
                      
                      return (
                        <div 
                          key={index} 
                          className="agent-evaluation-card"
                          data-agent-key={agentKey}
                        >
                          <div className="agent-card-header">
                            <div>
                              <h4>{agent.agent || 'Unknown Agent'}</h4>
                              <span className="agent-role">{agent.role || 'No role specified'}</span>
                              {agent.model && <span className="agent-model">Model: {agent.model}</span>}
                            </div>
                          </div>

                          {/* 显示 Analysis */}
                          {agent.analysis && Object.keys(agent.analysis).length > 0 ? (
                            <div className="agent-analysis">
                              {Object.entries(agent.analysis).map(([dimensionKey, dimensionValue]) => {
                                if (!dimensionValue || typeof dimensionValue !== 'object') {
                                  console.log(`Skipping ${dimensionKey}: not an object`, dimensionValue);
                                  return null;
                                }

                                const hasScore = dimensionValue.score !== undefined && dimensionValue.score !== null;
                                const hasStrengths = dimensionValue.strengths && dimensionValue.strengths.length > 0;
                                const hasImprovements = dimensionValue.areas_for_improvement && dimensionValue.areas_for_improvement.length > 0;
                                const hasGaps = dimensionValue.gaps && dimensionValue.gaps.length > 0;
                                const hasCulturalElements = dimensionValue.cultural_elements_present && dimensionValue.cultural_elements_present.length > 0;

                                if (!hasScore && !hasStrengths && !hasImprovements && !hasGaps && !hasCulturalElements) {
                                  console.log(`Skipping ${dimensionKey}: no content to display`);
                                  return null;
                                }

                                return (
                                  <div 
                                    key={dimensionKey} 
                                    className="analysis-dimension"
                                    data-dimension-key={dimensionKey}
                                  >
                                    <h5>{dimensionKey.replace(/_/g, ' ').toUpperCase()}</h5>
                                    
                                    {hasScore && (
                                      <div className="dimension-score-bar">
                                        <div 
                                          className="score-fill"
                                          style={{ 
                                            width: `${dimensionValue.score}%`,
                                            backgroundColor: getScoreColor(dimensionValue.score)
                                          }}
                                        >
                                          <span>{dimensionValue.score}/100</span>
                                        </div>
                                      </div>
                                    )}

                                    {hasStrengths && (
                                      <div className="analysis-section">
                                        <strong>✅ Strengths:</strong>
                                        <ul>
                                          {dimensionValue.strengths.map((item, i) => (
                                            <li key={i}>{item}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}

                                    {hasImprovements && (
                                      <div className="analysis-section">
                                        <strong>🔧 Areas for Improvement:</strong>
                                        <ul>
                                          {dimensionValue.areas_for_improvement.map((item, i) => (
                                            <li key={i}>{item}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}

                                    {hasGaps && (
                                      <div className="analysis-section warning">
                                        <strong>💡 Improvement Suggestions:</strong>
                                        <ul>
                                          {dimensionValue.gaps.map((item, i) => (
                                            <li key={i}>
                                              {item.replace(/⚠️\s*/g, '').replace(/🚩\s*/g, '').replace(/MISSING:\s*/g, '').replace(/CRITICAL:\s*/g, '')}
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}

                                    {hasCulturalElements && (
                                      <div className="analysis-section">
                                        <strong>🌏 Cultural Elements Present:</strong>
                                        <ul>
                                          {dimensionValue.cultural_elements_present.map((item, i) => (
                                            <li key={i}>{item}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="no-analysis">
                              <p>⚠️ No detailed analysis available from this agent.</p>
                              <p style={{fontSize: '0.85rem', marginTop: '0.5rem', color: '#94a3b8'}}>
                                Data received: {JSON.stringify(agent.analysis || {}).substring(0, 100)}...
                              </p>
                            </div>
                          )}

                          {/* Recommendations */}
                          {agent.recommendations && Array.isArray(agent.recommendations) && agent.recommendations.length > 0 && (
                            <div className="agent-recommendations">
                              <strong>
                                <Lightbulb size={18} style={{ display: 'inline-block', verticalAlign: 'middle', marginRight: '0.5rem' }} />
                                Recommendations ({agent.recommendations.length}):
                              </strong>
                              <ul>
                                {agent.recommendations.map((rec, i) => (
                                  <li key={i}>{rec}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* ✅ 新增：统一的Recommended Resources section（放在Agent Evaluations之后） */}
                {evaluationResult && evaluationResult.agent_responses && evaluationResult.agent_responses.length > 0 && (
                  <div className="unified-resources-section">
                    <h3>📚 Recommended Resources</h3>
                    <p className="resources-description">
                      Explore these curated New Zealand education resources to enhance your lesson planning:
                    </p>
                    <div className="resource-links">
                      {(() => {
                        // 收集所有agent的维度keys
                        const allDimensionKeys = [];
                        evaluationResult.agent_responses.forEach(agent => {
                          if (agent.analysis) {
                            allDimensionKeys.push(...Object.keys(agent.analysis));
                          }
                        });
                        
                        // 为每个维度获取推荐网站，然后去重
                        const allWebsites = [];
                        allDimensionKeys.forEach(key => {
                          allWebsites.push(...getRelevantWebsites(key, subjectArea));
                        });
                        
                        // 去重并限制为最多6个
                        const uniqueWebsites = Array.from(new Map(allWebsites.map(w => [w.url, w])).values());
                        return uniqueWebsites.slice(0, 6).map((website, i) => (
                          <a 
                            key={i} 
                            href={website.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="resource-link"
                          >
                            <Globe size={16} />
                            <span>{website.name}</span>
                          </a>
                        ));
                      })()}
                    </div>
                  </div>
                )}

                {/* Priority Recommendations */}
                {evaluationResult.debate_transcript?.consensus?.priority_recommendations && (
                  <div className="priority-recommendations-section">
                    <h3>⭐ Priority Recommendations</h3>
                    {evaluationResult.debate_transcript.consensus.priority_recommendations.map((rec, idx) => (
                      <div 
                        key={idx} 
                        className={`recommendation-card priority-${rec.priority.toLowerCase()}`}
                      >
                        <div className="recommendation-header">
                          <span className="priority-badge">{rec.priority}</span>
                          <h4>{rec.recommendation}</h4>
                        </div>
                        <p className="recommendation-rationale">{rec.rationale}</p>
                        {rec.resource && (
                          <div className="recommendation-resource">
                            <BookOpen size={16} />
                            <span>Resource: {rec.resource.replace(/_/g, ' ')}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* ✅ Generate Improved Lesson Button - 移到最后 */}
                <div className="improve-lesson-actions">
                  <h3>💡 Want an Improved Lesson Plan?</h3>
                  <p className="improve-lesson-description">
                    Generate an enhanced version of your lesson plan based on the evaluation feedback and recommendations.
                  </p>
                  <button
                    onClick={handleGenerateImprovedLesson}
                    disabled={isGenerating}
                    className="generate-improved-button"
                  >
                    {isGenerating ? (
                      <>
                        <Loader className="spinning" size={20} />
                        Generating Improved Lesson Plan...
                      </>
                    ) : (
                      <>
                        <Sparkles size={20} />
                        Generate Improved Lesson Plan
                      </>
                    )}
                  </button>
                </div>

                {/* ✅ 显示生成的Improved Lesson Plan - 移到Generate按钮之后 */}
                {(streamingText || improvedLesson) && (
                  <div className="improved-lesson-section">
                    <div className="improved-lesson-header">
                      <h3>✨ Improved Lesson Plan</h3>
                      {improvedLesson && (
                        <button 
                          className="download-button"
                          onClick={async () => {
                            try {
                              console.log('Starting download...');
                              const response = await fetch(`${API_BASE_URL}/api/convert-to-word`, {
                                method: 'POST',
                                headers: { 
                                  'Content-Type': 'application/json',
                                  'Accept': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                                },
                                body: JSON.stringify({
                                  content: improvedLesson,
                                  filename: 'Improved lesson plan.docx'  //统一文件名
                                })
                              });
                              
                              console.log('Response status:', response.status);
                              console.log('Response headers:', response.headers);
                              
                              if (!response.ok) {
                                throw new Error(`Server error: ${response.status}`);
                              }
                              
                              // 直接下载为 Word 文档
                              const blob = await response.blob();
                              console.log('Blob size:', blob.size, 'type:', blob.type);
                              
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.style.display = 'none';
                              a.href = url;
                              a.download = 'Improved lesson plan.docx'  //统一文件名;
                              
                              document.body.appendChild(a);
                              a.click();
                              
                              // 清理
                              window.URL.revokeObjectURL(url);
                              document.body.removeChild(a);
                              
                              console.log('✅ Download initiated successfully');
                            } catch (err) {
                              console.error('❌ Download error:', err);
                              // 如果 Word 下载失败，提供txt文本下载作为备选
                              alert(`Word download failed: ${err.message}\nDownloading as text file instead.`);
                              const blob = new Blob([improvedLesson], { type: 'text/plain' });
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.style.display = 'none';
                              a.href = url;
                              a.download = 'Improved lesson plan.docx'  //统一文件名;
                              document.body.appendChild(a);
                              a.click();
                              window.URL.revokeObjectURL(url);
                              document.body.removeChild(a);
                            }
                          }}
                        >
                          <Download size={16} />
                          Download
                        </button>
                      )}
                    </div>
                    <div 
                      className="improved-lesson-content"
                      ref={improvedLessonRef}
                    >
                      <pre>{streamingText || improvedLesson}</pre>
                      {/* ✅ 生成中显示加载动画 */}
                      {isGenerating && (
                        <div className="streaming-indicator">
                          <Loader className="spinning" size={16} />
                          <span>Generating...</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>
          Powered by Multi-Agent AI (Claude, DeepSeek, GPT-4) | 
          New Zealand Education Context | SQLite Database
        </p>
      </footer>
    </div>
  );
}

export default App;