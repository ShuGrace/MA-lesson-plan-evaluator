import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send,
  BookOpen,
  Users,
  Globe,
  AlertCircle,
  CheckCircle,
  Loader,
  History,
  Target,
  Brain,
  Upload,
  FileCheck,
  X,
  Download,
  Sparkles,
  Lightbulb,
  FileSpreadsheet,
  FileText,
} from 'lucide-react';
import './app.css';

const API_BASE_URL = 'http://localhost:8000';

const IS_DEV = import.meta.env.DEV;
const log = (...args) => {
  if (IS_DEV) console.log(...args);
};

// ────────────────────────────────────────────
// Recommended Websites (unchanged)
// ────────────────────────────────────────────
const RECOMMENDED_WEBSITES = {
  maori_language: [
    { url: 'https://maoridictionary.co.nz', name: 'Te Aka Māori Dictionary' },
    { url: 'https://tereomaori.tki.org.nz', name: 'Te Reo Māori - TKI' },
    { url: 'https://tematawai.maori.nz', name: 'Te Mātāwai' },
  ],
  cultural: [
    { url: 'https://teara.govt.nz', name: 'Te Ara - Encyclopedia of NZ' },
    { url: 'https://nzhistory.govt.nz', name: 'NZ History' },
    { url: 'https://aucklandmuseum.com', name: 'Auckland Museum' },
  ],
  curriculum: [
    { url: 'https://nzcurriculum.tki.org.nz', name: 'NZ Curriculum Online' },
    { url: 'https://tki.org.nz', name: 'TKI - Te Kete Ipurangi' },
    { url: 'https://education.govt.nz', name: 'Ministry of Education' },
  ],
  science: [
    { url: 'https://sciencelearn.org.nz', name: 'Science Learning Hub' },
    { url: 'https://scienceonline.tki.org.nz', name: 'Science Online' },
  ],
  mathematics: [{ url: 'https://nzmaths.co.nz', name: 'NZ Maths' }],
  literacy: [
    { url: 'https://englishonline.tki.org.nz', name: 'English Online' },
    { url: 'https://literacyonline.tki.org.nz', name: 'Literacy Online' },
  ],
  arts: [{ url: 'https://artsonline.tki.org.nz', name: 'Arts Online' }],
  assessment: [
    { url: 'https://nzqa.govt.nz', name: 'NZQA' },
    { url: 'https://ero.govt.nz', name: 'ERO' },
  ],
  professional: [
    { url: 'https://teachingcouncil.nz', name: 'Teaching Council NZ' },
    { url: 'https://nzcer.org.nz', name: 'NZCER' },
  ],
  sustainability: [
    { url: 'https://enviroschools.org.nz', name: 'Enviroschools' },
    { url: 'https://sustainability.tki.org.nz', name: 'Sustainability - TKI' },
  ],
  instructional_design: [
    { url: 'https://www.ascd.org/', name: 'ASCD - Learning & Teaching' },
    { url: 'https://www.edutopia.org/', name: 'Edutopia - Instructional Design' },
  ],
};

const getRelevantWebsites = (dimensionKey, subjectArea) => {
  const websites = [];

  if (dimensionKey === 'place_based_learning') {
    websites.push(...RECOMMENDED_WEBSITES.cultural);
    if (subjectArea?.toLowerCase().includes('science')) {
      websites.push(...RECOMMENDED_WEBSITES.science);
    }
    websites.push(...RECOMMENDED_WEBSITES.sustainability);
  } else if (
    dimensionKey === 'cultural_responsiveness_integrated' ||
    dimensionKey === 'cultural_responsiveness'
  ) {
    websites.push(...RECOMMENDED_WEBSITES.maori_language);
    websites.push(...RECOMMENDED_WEBSITES.cultural);
  } else if (dimensionKey === 'critical_pedagogy') {
    websites.push(...RECOMMENDED_WEBSITES.curriculum);
    websites.push(...RECOMMENDED_WEBSITES.professional);
  } else if (dimensionKey === 'lesson_design_quality') {
    websites.push(...RECOMMENDED_WEBSITES.curriculum);
    websites.push(...RECOMMENDED_WEBSITES.instructional_design);
  }

  const uniqueWebsites = Array.from(
    new Map(websites.map((w) => [w.url, w])).values()
  );
  return uniqueWebsites.slice(0, 3);
};

// ────────────────────────────────────────────
// Score card configuration (static, hoisted)
// ────────────────────────────────────────────
const SCORE_CONFIG = [
  {
    key: 'place_based_learning',
    label: 'Place-Based Learning',
    icon: <Globe size={24} />,
  },
  {
    key: 'cultural_responsiveness_integrated',
    label: 'Cultural Responsiveness & Māori Perspectives',
    icon: <Users size={24} />,
  },
  {
    key: 'critical_pedagogy',
    label: 'Critical Pedagogy',
    icon: <Brain size={24} />,
  },
  {
    key: 'lesson_design_quality',
    label: 'Lesson Design Quality',
    icon: <FileSpreadsheet size={24} />,
  },
];

const VALID_FILE_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
];

// ────────────────────────────────────────────
// Helper: score colour / label
// ────────────────────────────────────────────
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

// ────────────────────────────────────────────
// Reusable sub-components
// ────────────────────────────────────────────

/** Circular score ring used in every score card */
const ScoreRing = ({ score }) => {
  const circumference = 2 * Math.PI * 60;
  return (
    <div className="circular-progress">
      <svg width="140" height="140">
        <circle cx="70" cy="70" r="60" fill="none" stroke="#e5e7eb" strokeWidth="12" />
        <circle
          cx="70"
          cy="70"
          r="60"
          fill="none"
          stroke={getScoreColor(score)}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - score / 100)}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
        />
      </svg>
      <div className="score-value">{score}</div>
    </div>
  );
};

/** Common form fields shared between text & file input modes */
const CommonFormFields = ({
  lessonTitle,
  setLessonTitle,
  gradeLevel,
  setGradeLevel,
  subjectArea,
  setSubjectArea,
  idPrefix,
}) => (
  <>
    <div className="form-group">
      <label htmlFor={`${idPrefix}-lesson-title`}>Lesson Title *</label>
      <input
        id={`${idPrefix}-lesson-title`}
        type="text"
        placeholder="e.g., Water Quality Investigation"
        value={lessonTitle}
        onChange={(e) => setLessonTitle(e.target.value)}
        className="input-field"
      />
    </div>

    <div className="form-row">
      <div className="form-group">
        <label htmlFor={`${idPrefix}-grade-level`}>Grade Level</label>
        <input
          id={`${idPrefix}-grade-level`}
          type="text"
          placeholder="e.g., Year 7-8"
          value={gradeLevel}
          onChange={(e) => setGradeLevel(e.target.value)}
          className="input-field"
        />
      </div>
      <div className="form-group">
        <label htmlFor={`${idPrefix}-subject-area`}>Subject Area</label>
        <input
          id={`${idPrefix}-subject-area`}
          type="text"
          placeholder="e.g., Science"
          value={subjectArea}
          onChange={(e) => setSubjectArea(e.target.value)}
          className="input-field"
        />
      </div>
    </div>
  </>
);

// ────────────────────────────────────────────
// Main App component
// ────────────────────────────────────────────
function App() {
  // ── form state ──
  const [lessonTitle, setLessonTitle] = useState('');
  const [lessonContent, setLessonContent] = useState('');
  const [gradeLevel, setGradeLevel] = useState('');
  const [subjectArea, setSubjectArea] = useState('');

  // ── evaluation state ──
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [error, setError] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);

  // ── history ──
  const [savedEvaluations, setSavedEvaluations] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  // ── file upload ──
  const [inputMode, setInputMode] = useState('text');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [extractedText, setExtractedText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const fileInputRef = useRef(null);

  // ── AI provider ──
  const [selectedProvider, setSelectedProvider] = useState('gpt');

  // ── evaluation mode ──
  const [evaluationMode, setEvaluationMode] = useState('standard');

  // ── improved lesson ──
  const [isGenerating, setIsGenerating] = useState(false);
  const [improvedLesson, setImprovedLesson] = useState(null);
  const [streamingText, setStreamingText] = useState('');
  const improvedLessonRef = useRef(null);

  // ── AbortController for in-flight requests ──
  const abortControllerRef = useRef(null);

  // ────────────────────────────────────────
  // Cleanup: abort any pending request on unmount
  // ────────────────────────────────────────
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // ────────────────────────────────────────
  // Load saved evaluations
  // ────────────────────────────────────────
  const loadSavedEvaluations = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/evaluations?limit=20`);
      if (response.ok) {
        const data = await response.json();
        setSavedEvaluations(data.evaluations || data);
      }
    } catch (err) {
      log('Failed to load saved evaluations:', err);
    }
  }, []);

  useEffect(() => {
    loadSavedEvaluations();
  }, [loadSavedEvaluations]);

  // ── auto-scroll streaming area ──
  useEffect(() => {
    if (improvedLessonRef.current && streamingText) {
      improvedLessonRef.current.scrollTop = improvedLessonRef.current.scrollHeight;
    }
  }, [streamingText]);

  // ────────────────────────────────────────
  // Input mode switching
  // ────────────────────────────────────────
  const handleInputModeChange = (mode) => {
    setInputMode(mode);
    setEvaluationResult(null);
    setError(null);
    setSaveStatus(null);
    setImprovedLesson(null);
    setStreamingText('');
    if (mode === 'text') {
      setUploadedFile(null);
      setExtractedText('');
      setLessonContent('');
    }
  };

  // ────────────────────────────────────────
  // File upload helpers
  // ────────────────────────────────────────
  const processFile = useCallback(async (file) => {
    if (!VALID_FILE_TYPES.includes(file.type)) {
      setError('Only PDF and Word (.docx, .doc) files are supported');
      return;
    }

    setUploadedFile(file);
    setError(null);
    setIsExtracting(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const formData = new FormData();
    formData.append('file', file);

    try {
      log('Uploading file:', file.name);

      const response = await fetch(`${API_BASE_URL}/api/extract-text`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      log('Upload response status:', response.status);

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      log('Extracted text length:', data.text?.length);

      setExtractedText(data.text);
      setLessonContent(data.text);

      if (data.metadata?.title) {
        setLessonTitle(data.metadata.title);
      }

      setError(null);
      log('File processed successfully');
    } catch (err) {
      if (err.name === 'AbortError') return; // component unmounted / user cancelled

      log('File processing error:', err);

      const errorMessage = err.message.includes('Failed to fetch')
        ? 'Cannot connect to server. Please check the backend is running.'
        : err.message;

      setError(errorMessage);
      setUploadedFile(null);
      setExtractedText('');
      setLessonContent('');
    } finally {
      setIsExtracting(false);
    }
  }, []);

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) await processFile(file);
  };

  const handleFileDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) await processFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const clearUploadedFile = () => {
    setUploadedFile(null);
    setExtractedText('');
    if (inputMode === 'file') {
      setLessonContent('');
    }
  };

  // ────────────────────────────────────────
  // Evaluate
  // ────────────────────────────────────────
  const handleEvaluate = async () => {
    const contentToEvaluate = lessonContent;

    if (!lessonTitle.trim() || !contentToEvaluate.trim()) {
      setError('Please enter both lesson title and content');
      return;
    }

    // abort any previous request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsEvaluating(true);
    setError(null);
    setEvaluationResult(null);
    setSaveStatus(null);
    setImprovedLesson(null);
    setStreamingText('');

    try {
      // Choose endpoint based on evaluation mode
      const endpoint = evaluationMode === 'debate'
        ? `${API_BASE_URL}/api/evaluate/lesson-debate`
        : `${API_BASE_URL}/api/evaluate/lesson`;

      const evalResponse = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lesson_plan_text: contentToEvaluate,
          lesson_plan_title: lessonTitle,
          grade_level: gradeLevel,
          subject_area: subjectArea,
          provider: selectedProvider,
        }),
        signal: controller.signal,
      });

      if (!evalResponse.ok) {
        let errorMessage = `Evaluation failed (${evalResponse.status})`;
        try {
          const errorData = await evalResponse.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          const errorText = await evalResponse.text();
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const result = await evalResponse.json();
      setEvaluationResult(result);
      setSaveStatus({
        type: 'success',
        message: `Evaluation saved (Provider: ${selectedProvider.toUpperCase()}, Mode: ${evaluationMode === 'debate' ? 'Multi-Agent Debate' : 'Standard'})`,
      });
      loadSavedEvaluations();
    } catch (err) {
      if (err.name === 'AbortError') return;

      log('Evaluation error:', err);

      const errorMessage = err.message.includes('Failed to fetch')
        ? 'Cannot connect to server. Please check the backend is running on http://localhost:8000'
        : err.message;

      setError(errorMessage);
    } finally {
      setIsEvaluating(false);
    }
  };

  // ────────────────────────────────────────
  // Generate improved lesson plan
  // ────────────────────────────────────────
  const handleGenerateImprovedLesson = async () => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsGenerating(true);
    setError(null);
    setStreamingText('');
    setImprovedLesson(null);

    try {
      const allRecommendations = [];

      evaluationResult.agent_responses.forEach((agent) => {
        if (agent.recommendations) {
          allRecommendations.push(...agent.recommendations);
        }

        if (agent.analysis) {
          Object.values(agent.analysis).forEach((dimension) => {
            if (dimension.gaps) allRecommendations.push(...dimension.gaps);
            if (dimension.areas_for_improvement)
              allRecommendations.push(...dimension.areas_for_improvement);
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
          remove_numbering: true,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to generate improved lesson');
      }

      const contentType = response.headers.get('content-type');

      if (
        response.body &&
        contentType &&
        contentType.includes('text/event-stream')
      ) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;
            setStreamingText(fullText);
          }
        } catch (readErr) {
          if (readErr.name === 'AbortError') return;
          throw readErr;
        } finally {
          reader.releaseLock();
        }

        setImprovedLesson(fullText);
      } else {
        const data = await response.json();
        setImprovedLesson(data.improved_lesson);
        setStreamingText(data.improved_lesson);
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(`Failed to generate improved lesson plan: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // ────────────────────────────────────────
  // Download improved lesson as Word
  // ────────────────────────────────────────
  const handleDownloadImprovedLesson = async () => {
    try {
      log('Starting download...');
      const response = await fetch(`${API_BASE_URL}/api/convert-to-word`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept:
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        },
        body: JSON.stringify({
          content: improvedLesson,
          filename: 'Improved_Lesson_Plan.docx',
        }),
      });

      log('Response status:', response.status);

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const blob = await response.blob();
      log('Blob size:', blob.size, 'type:', blob.type);
      triggerDownload(blob, 'Improved_Lesson_Plan.docx');
      log('Download initiated successfully');
    } catch (err) {
      log('Download error:', err);
      alert(
        `Word download failed: ${err.message}\nDownloading as text file instead.`
      );
      const blob = new Blob([improvedLesson], { type: 'text/plain' });
      triggerDownload(blob, 'Improved_Lesson_Plan.txt');
    }
  };

  /** Create a temporary <a> to trigger a browser download */
  const triggerDownload = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  // ────────────────────────────────────────
  // Click-to-scroll for score cards
  // ────────────────────────────────────────
  const handleScoreCardClick = (agentKey) => {
    if (agentKey === 'overall') {
      const resultsSection = document.querySelector('.results-section');
      resultsSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      const dimensionSection = document.querySelector(
        `[data-dimension-key="${agentKey}"]`
      );
      if (dimensionSection) {
        dimensionSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        log(`Dimension section not found for key: ${agentKey}`);
      }
    }
  };

  // ────────────────────────────────────────
  // Render helpers
  // ────────────────────────────────────────

  /** Resolve score for a config entry (handles key aliases) */
  const resolveScore = (configKey, scores) => {
    let score = scores[configKey];
    if (
      configKey === 'cultural_responsiveness_integrated' &&
      (score === undefined || score === null)
    ) {
      score = scores['cultural_responsiveness'];
    }
    return score;
  };

  const renderScoreCards = () => {
    if (!evaluationResult?.scores) return null;

    const validScores = SCORE_CONFIG.filter((config) => {
      const score = resolveScore(config.key, evaluationResult.scores);
      return score !== undefined && score !== null && score > 0;
    });

    if (validScores.length === 0) return null;

    const scoreCards = validScores.map((config) => {
      const score = resolveScore(config.key, evaluationResult.scores);

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
          <ScoreRing score={score} />
          <div className="score-label" style={{ color: getScoreColor(score) }}>
            {getScoreLabel(score)}
          </div>
        </div>
      );
    });

    // Overall score
    if (evaluationResult.scores?.overall) {
      const overall = evaluationResult.scores.overall;
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
          <ScoreRing score={overall} />
          <div className="score-label" style={{ color: getScoreColor(overall) }}>
            {getScoreLabel(overall)}
          </div>
        </div>
      );
    }

    return scoreCards;
  };

  /** Extract the primary dimension key from an agent response */
  const getAgentKey = (agent) => {
    if (agent.dimension) return agent.dimension;
    if (agent.dimensions?.length > 0) return agent.dimensions[0];
    if (agent.analysis) {
      const keys = Object.keys(agent.analysis);
      if (keys.length > 0) return keys[0];
    }
    return '';
  };

  /** Render a single analysis dimension block */
  const renderDimension = (dimensionKey, dimensionValue) => {
    if (!dimensionValue || typeof dimensionValue !== 'object') return null;

    const hasScore =
      dimensionValue.score !== undefined && dimensionValue.score !== null;
    const hasStrengths = dimensionValue.strengths?.length > 0;
    const hasImprovements = dimensionValue.areas_for_improvement?.length > 0;
    const hasGaps = dimensionValue.gaps?.length > 0;
    const hasCulturalElements =
      dimensionValue.cultural_elements_present?.length > 0;

    if (
      !hasScore &&
      !hasStrengths &&
      !hasImprovements &&
      !hasGaps &&
      !hasCulturalElements
    ) {
      return null;
    }

    const dimensionTitles = {
      'place_based_learning': 'PLACE BASED LEARNING',
      'cultural_responsiveness_integrated': 'CULTURAL RESPONSIVENESS & MĀORI PERSPECTIVES',
      'cultural_responsiveness': 'CULTURAL RESPONSIVENESS & MĀORI PERSPECTIVES',
      'critical_pedagogy': 'CRITICAL PEDAGOGY',
      'lesson_design_quality': 'LESSON DESIGN QUALITY',
    };

    const dimensionDescriptions = {
      'place_based_learning':
        'This dimension evaluates how effectively the lesson plan connects learning to local places, environments, and community contexts in Aotearoa New Zealand.',
      'cultural_responsiveness_integrated':
        'This unified dimension encompasses both general cultural responsiveness and Māori perspectives, reflecting Aotearoa New Zealand\'s bicultural educational context.',
      'cultural_responsiveness':
        'This unified dimension encompasses both general cultural responsiveness and Māori perspectives, reflecting Aotearoa New Zealand\'s bicultural educational context.',
      'critical_pedagogy':
        'This dimension evaluates how the lesson plan promotes critical thinking, student agency, and examination of multiple perspectives and power dynamics.',
      'lesson_design_quality':
        'This dimension evaluates the technical quality and structural soundness of the lesson plan as an instructional document.',
    };

    const title = dimensionTitles[dimensionKey] || dimensionKey.replace(/_/g, ' ').toUpperCase();
    const description = dimensionDescriptions[dimensionKey] || '';

    return (
      <div
        key={dimensionKey}
        className="analysis-dimension"
        data-dimension-key={dimensionKey}
      >
        <h5>{title}</h5>

        {description && (
          <p className="dimension-description">{description}</p>
        )}

        {hasScore && (
          <div className="dimension-score-bar">
            <div
              className="score-fill"
              style={{
                width: `${dimensionValue.score}%`,
                backgroundColor: getScoreColor(dimensionValue.score),
              }}
            >
              <span>{dimensionValue.score}/100</span>
            </div>
          </div>
        )}

        {hasStrengths && (
          <div className="analysis-section strengths-section">
            <strong>Strengths:</strong>
            <ul>
              {dimensionValue.strengths.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {hasImprovements && (
          <div className="analysis-section areas-section">
            <strong>Areas for Improvement:</strong>
            <ul>
              {dimensionValue.areas_for_improvement.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {hasGaps && (
          <div className="analysis-section warning">
            <strong>Improvement Suggestions:</strong>
            <ul>
              {dimensionValue.gaps.map((item, i) => (
                <li key={i}>
                  {item
                    .replace(/⚠️\s*/g, '')
                    .replace(/🚩\s*/g, '')
                    .replace(/MISSING:\s*/g, '')
                    .replace(/CRITICAL:\s*/g, '')}
                </li>
              ))}
            </ul>
          </div>
        )}

        {hasCulturalElements && (
          <div className="analysis-section">
            <strong>Cultural Elements Present:</strong>
            <ul>
              {dimensionValue.cultural_elements_present.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  // ────────────────────────────────────────
  // Collect unique recommended resources
  // ────────────────────────────────────────
  const getUniqueRecommendedResources = () => {
    if (!evaluationResult?.agent_responses?.length) return [];

    const allDimensionKeys = [];
    evaluationResult.agent_responses.forEach((agent) => {
      if (agent.analysis) {
        allDimensionKeys.push(...Object.keys(agent.analysis));
      }
    });

    const allWebsites = [];
    allDimensionKeys.forEach((key) => {
      allWebsites.push(...getRelevantWebsites(key, subjectArea));
    });

    return Array.from(
      new Map(allWebsites.map((w) => [w.url, w])).values()
    ).slice(0, 6);
  };

  // ══════════════════════════════════════��═
  //  JSX
  // ════════════════════════════════════════
  return (
    <div className="app-container">
      {/* ── Header ── */}
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

      {/* ── Main ── */}
      <main className="main-content-centered">
        <div className="content-wrapper">
          {/* History sidebar */}
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
                  {savedEvaluations.map((evaluation) => (
                    <div key={evaluation.id} className="history-item">
                      <div className="history-item-header">
                        <strong>
                          {evaluation.lesson_plan_title || 'Untitled'}
                        </strong>
                        <span className="status-badge status-completed">
                          Completed
                        </span>
                      </div>
                      <div className="history-item-meta">
                        {evaluation.grade_level && (
                          <span>Grade: {evaluation.grade_level}</span>
                        )}
                        {evaluation.subject_area && (
                          <span>Subject: {evaluation.subject_area}</span>
                        )}
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
            {/* ──────────────── Input Section ──────────────── */}
            <div className="input-section">
              <h2>Lesson Plan Input</h2>

              {/* Tab switcher */}
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

              {/* ── Text input mode ── */}
              {inputMode === 'text' ? (
                <>
                  <CommonFormFields
                    lessonTitle={lessonTitle}
                    setLessonTitle={setLessonTitle}
                    gradeLevel={gradeLevel}
                    setGradeLevel={setGradeLevel}
                    subjectArea={subjectArea}
                    setSubjectArea={setSubjectArea}
                    idPrefix="text"
                  />

                  <div className="form-group">
                    <label htmlFor="text-lesson-content">
                      Lesson Plan Content *
                    </label>
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
                /* ── File upload mode ── */
                <>
                  <CommonFormFields
                    lessonTitle={lessonTitle}
                    setLessonTitle={setLessonTitle}
                    gradeLevel={gradeLevel}
                    setGradeLevel={setGradeLevel}
                    subjectArea={subjectArea}
                    setSubjectArea={setSubjectArea}
                    idPrefix="file"
                  />

                  <div
                    className={`file-drop-zone ${isDragging ? 'dragging' : ''} ${
                      uploadedFile ? 'has-file' : ''
                    }`}
                    onDrop={handleFileDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() =>
                      !uploadedFile && fileInputRef.current?.click()
                    }
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
                        <p className="file-size">
                          {(uploadedFile.size / 1024).toFixed(1)} KB
                        </p>
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

              {/* ── Provider selector (shared) ── */}
              <div className="provider-selector">
                <h3>Select AI Provider</h3>
                <p className="provider-description">
                  Choose which AI system will evaluate all 4 dimensions of your
                  lesson plan
                </p>
                                <div className="provider-buttons">
                  <button
                    type="button"
                    className={`provider-button ${
                      selectedProvider === 'gpt' ? 'active' : ''
                    }`}
                    onClick={() => setSelectedProvider('gpt')}
                    disabled={isEvaluating}
                  >
                    <span className="provider-icon">GPT</span>
                    <div className="provider-info">
                      <strong>GPT 4o</strong>
                      <small>
                        All 4 dimensions evaluated by OpenAI GPT-4o
                      </small>
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`provider-button ${
                      selectedProvider === 'claude' ? 'active' : ''
                    }`}
                    onClick={() => setSelectedProvider('claude')}
                    disabled={isEvaluating}
                  >
                    <span className="provider-icon">CLAUDE</span>
                    <div className="provider-info">
                      <strong>Claude Sonnet 4</strong>
                      <small>
                        All 4 dimensions evaluated by Anthropic Claude
                      </small>
                    </div>
                  </button>
                </div>
                <div className="provider-note">
                  <AlertCircle size={16} />
                  <span>
                    <strong>Ensemble Mode:</strong> Both systems use identical
                    evaluation frameworks. Run both to compare results and
                    increase confidence.
                  </span>
                </div>
              </div>
              
              {/* debate */}
              {/* ── Evaluation Mode selector ── */}
              <div className="provider-selector">
                <h3>Evaluation Mode</h3>
                <p className="provider-description">
                  Choose how agents evaluate your lesson plan
                </p>
                <div className="provider-buttons">
                  <button
                    type="button"
                    className={`provider-button ${
                      evaluationMode === 'standard' ? 'active' : ''
                    }`}
                    onClick={() => setEvaluationMode('standard')}
                    disabled={isEvaluating}
                  >
                    <span className="provider-icon">⚡</span>
                    <div className="provider-info">
                      <strong>Standard</strong>
                      <small>Independent evaluation, faster (~30s)</small>
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`provider-button ${
                      evaluationMode === 'debate' ? 'active' : ''
                    }`}
                    onClick={() => setEvaluationMode('debate')}
                    disabled={isEvaluating}
                  >
                    <span className="provider-icon">🤝</span>
                    <div className="provider-info">
                      <strong>Multi-Agent Debate</strong>
                      <small>Agents discuss & reach consensus (~90s)</small>
                    </div>
                  </button>
                </div>
              </div>

              {/* ── Submit ── */}
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

              {saveStatus?.type === 'success' && (
                <div className="success-message">
                  <CheckCircle size={20} />
                  <span>{saveStatus.message}</span>
                </div>
              )}
            </div>

            {/* ──────────────── Results Section ──────────────── */}
            {evaluationResult && (
              <div className="results-section">
                <h2>Evaluation Results</h2>

                {/* Score cards */}
                <div className="scores-grid">{renderScoreCards()}</div>

                {/* Agent evaluations */}
                {evaluationResult.agent_responses?.length > 0 && (
                  <div className="agent-evaluations-section">
                    <h3> Agent Evaluations</h3>
                    {evaluationResult.agent_responses.map((agent, index) => {
                      const agentKey = getAgentKey(agent);

                      // Map dimension key to clean display name
                      const dimensionLabels = {
                        'place_based_learning': 'Place-Based Learning',
                        'cultural_responsiveness_integrated': 'Cultural Responsiveness & Māori Perspectives',
                        'cultural_responsiveness': 'Cultural Responsiveness & Māori Perspectives',
                        'critical_pedagogy': 'Critical Pedagogy',
                        'lesson_design_quality': 'Lesson Design Quality',
                      };

                      const displayName = dimensionLabels[agentKey] || agentKey.replace(/_/g, ' ');

                      return (
                        <div
                          key={index}
                          className="agent-evaluation-card"
                          data-agent-key={agentKey}
                        >
                          <div className="agent-card-header">
                            <div>
                              <h4>{displayName}</h4>
                            </div>
                          </div>

                          {/* Analysis dimensions */}
                          {agent.analysis &&
                          Object.keys(agent.analysis).length > 0 ? (
                            <div className="agent-analysis">
                              {Object.entries(agent.analysis).map(
                                ([dimensionKey, dimensionValue]) =>
                                  renderDimension(dimensionKey, dimensionValue)
                              )}
                            </div>
                          ) : agent.response ? (
                            <div className="agent-response-fallback">
                              <h5> Evaluation Response:</h5>
                              <pre className="agent-response-pre">
                                {agent.response}
                              </pre>
                            </div>
                          ) : (
                            <div className="no-analysis">
                              <p>
                                ⚠️ No detailed analysis available from this
                                agent.
                              </p>
                              <p className="no-analysis-debug">
                                Data received:{' '}
                                {JSON.stringify(agent.analysis || {}).substring(
                                  0,
                                  100
                                )}
                                ...
                              </p>
                            </div>
                          )}

                          {/* Recommendations */}
                          {agent.recommendations?.length > 0 && (
                            <div className="analysis-section recommendations-section">
                              <strong>
                                <Lightbulb
                                  size={18}
                                  style={{
                                    display: 'inline-block',
                                    verticalAlign: 'middle',
                                    marginRight: '0.5rem',
                                  }}
                                />
                                Recommendations (
                                {agent.recommendations.length}):
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

                {/* Recommended resources */}
                {evaluationResult.agent_responses?.length > 0 && (
                  <div className="unified-resources-section">
                    <h3> Recommended Resources</h3>
                    <p className="resources-description">
                      Explore these curated New Zealand education resources to
                      enhance your lesson planning:
                    </p>
                    <div className="resource-links">
                      {getUniqueRecommendedResources().map((website, i) => (
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
                      ))}
                    </div>
                  </div>
                )}

                {/* Priority recommendations */}
                {evaluationResult.debate_transcript?.consensus
                  ?.priority_recommendations && (
                  <div className="priority-recommendations-section">
                    <h3>⭐ Priority Recommendations</h3>
                    {evaluationResult.debate_transcript.consensus.priority_recommendations.map(
                      (rec, idx) => (
                        <div
                          key={idx}
                          className={`recommendation-card priority-${rec.priority.toLowerCase()}`}
                        >
                          <div className="recommendation-header">
                            <span className="priority-badge">
                              {rec.priority}
                            </span>
                            <h4>{rec.recommendation}</h4>
                          </div>
                          <p className="recommendation-rationale">
                            {rec.rationale}
                          </p>
                          {rec.resource && (
                            <div className="recommendation-resource">
                              <BookOpen size={16} />
                              <span>
                                Resource: {rec.resource.replace(/_/g, ' ')}
                              </span>
                            </div>
                          )}
                        </div>
                      )
                    )}
                  </div>
                )}

                {/* Generate improved lesson */}
                <div className="improve-lesson-actions">
                  <h3>Want an Improved Lesson Plan?</h3>
                  <p className="improve-lesson-description">
                    Generate an enhanced version of your lesson plan based on the
                    evaluation feedback and recommendations.
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

                {/* Improved lesson display */}
                {(streamingText || improvedLesson) && (
                  <div className="improved-lesson-section">
                    <div className="improved-lesson-header">
                      <h3>✨ Improved Lesson Plan</h3>
                      {improvedLesson && (
                        <button
                          className="download-button"
                          onClick={handleDownloadImprovedLesson}
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

      {/* ── Footer ── */}
      <footer className="app-footer">
        <p>
          Powered by Multi-Agent AI | Designed for New Zealand Education Context
          <br />
          Disclaimer: AI may make mistakes. The generated content needs to be reviewed before use. 
         
          Please consult with local iwi and cultural advisors for Māori content.
        </p>
      </footer>
    </div>
  );
}

export default App;