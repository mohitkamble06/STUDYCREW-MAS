"""API client for StudyCrew backend."""

const API_BASE = '/api'

type RequestOptions = RequestInit & {
  params?: Record<string, string>
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => url.searchParams.append(key, value))
  }

  const response = await fetch(url.toString(), {
    headers: {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
    ...fetchOptions,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export const api = {
  get: <T>(endpoint: string, params?: Record<string, string>) =>
    request<T>(endpoint, { method: 'GET', params }),

  post: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, { method: 'POST', body: JSON.stringify(data) }),

  put: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, { method: 'PUT', body: JSON.stringify(data) }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),

  // SSE helper
  createEventSource: (endpoint: string) => new EventSource(`${API_BASE}${endpoint}`),
}

// Course endpoints
export const coursesApi = {
  list: () => api.get<Course[]>('/courses'),
  get: (id: string) => api.get<Course>(`/courses/${id}`),
  create: (data: CourseCreate) => api.post<Course>('/courses', data),
  delete: (id: string) => api.delete(`/courses/${id}`),
}

// Upload endpoints
export const uploadsApi = {
  upload: (courseId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return fetch(`${API_BASE}/courses/${courseId}/upload`, {
      method: 'POST',
      body: formData,
    }).then(r => r.json())
  },
  list: (courseId: string) => api.get<UploadedDoc[]>(`/courses/${courseId}/uploads`),
  delete: (courseId: string, docId: string) => api.delete(`/courses/${courseId}/uploads/${docId}`),
}

// Run endpoints
export const runsApi = {
  create: (data: RunCreate) => api.post<Run>('/runs', data),
  get: (id: string) => api.get<Run>(`/runs/${id}`),
  execute: (id: string) => api.post(`/runs/${id}/execute`),
  streamEvents: (id: string) => api.createEventSource(`/runs/${id}/events`),
}

// Topic endpoints
export const topicsApi = {
  get: (id: string) => api.get<Topic>(`/topics/${id}`),
  getContent: (id: string) => api.get<TopicContent>(`/topics/${id}/content`),
  askFollowUp: (id: string, question: string) =>
    api.post<FollowUpResponse>(`/topics/${id}/ask`, { question }),
}

// Quiz endpoints
export const quizzesApi = {
  generate: (data: QuizGenerateRequest) => api.post<Quiz>('/quizzes/generate', data),
  submit: (attemptId: string, data: QuizSubmitRequest) =>
    api.post<QuizSubmitResponse>(`/quizzes/${attemptId}/submit`, data),
  getAttempt: (attemptId: string) => api.get<QuizAttempt>(`/quizzes/${attemptId}`),
}

// Progress endpoints
export const progressApi = {
  getPlan: (courseId: string) => api.get<StudyPlan>(`/courses/${courseId}/plan`),
  replan: (courseId: string) => api.post<StudyPlan>(`/courses/${courseId}/replan`),
  getProgress: (courseId: string) => api.get<ProgressSnapshot>(`/courses/${courseId}/progress`),
}

// Types
export interface Course {
  id: string
  subject: string
  exam_date: string
  hours_per_day: number
  level: 'beginner' | 'intermediate' | 'advanced'
  created_at: string
  topics: Topic[]
}

export interface CourseCreate {
  subject: string
  exam_date: string
  hours_per_day: number
  level: 'beginner' | 'intermediate' | 'advanced'
  topics: TopicCreate[]
}

export interface Topic {
  id: string
  course_id: string
  name: string
  importance: number
  mastery: number
}

export interface TopicCreate {
  name: string
  importance?: number
  mastery?: number
}

export interface UploadedDoc {
  id: string
  course_id: string
  filename: string
  chunk_count: number
  uploaded_at: string
}

export interface Run {
  id: string
  course_id: string
  status: 'running' | 'completed' | 'failed'
  created_at: string
  completed_at: string | null
  error: string | null
}

export interface RunCreate {
  course_id: string
}

export interface AgentEvent {
  run_id: string
  agent: string
  status: 'started' | 'done' | 'error'
  message: string
  topic_id: string | null
  timestamp: string
  data: Record<string, unknown>
}

export interface TopicContent {
  notes: TopicNotes
  explanation: Explanation
}

export interface TopicNotes {
  topic: string
  summary: string
  key_points: string[]
  definitions: string[]
  formulas_or_examples: string[]
  sources: SourceRef[]
}

export interface SourceRef {
  type: 'uploaded' | 'model_knowledge'
  doc_id: string | null
  chunk_id: string | null
  excerpt: string
}

export interface Explanation {
  explanation_markdown: string
  example: string
  common_mistakes: string[]
  check_question: string
}

export interface FollowUpRequest {
  question: string
}

export interface FollowUpResponse {
  answer: string
}

export interface QuizGenerateRequest {
  topic_id: string
  num_questions?: number
  difficulty?: 'easy' | 'medium' | 'hard'
}

export interface Quiz {
  topic_id: string
  questions: QuizQuestion[]
}

export interface QuizQuestion {
  id: string
  question: string
  options: string[]
  correct_index: number
  explanation: string
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface QuizSubmitRequest {
  attempt_id: string
  answers: Record<string, number>
}

export interface QuizSubmitResponse {
  score: number
  correct_count: number
  total_questions: number
  explanations: Record<string, string>
  new_mastery: number
}

export interface QuizAttempt {
  id: string
  topic_id: string
  quiz_json: Quiz
  answers_json: Record<string, number> | null
  score: number | null
  created_at: string
}

export interface StudyPlan {
  days: DayPlan[]
  total_days: number
  total_minutes: number
  warnings: string[]
}

export interface DayPlan {
  date: string
  topics: string[]
  minutes: number
  activity: 'learn' | 'revise' | 'practice' | 'mock_test'
  reason: string
}

export interface ProgressSnapshot {
  course_id: string
  days_remaining: number
  topic_masteries: Record<string, number>
  quiz_history: QuizHistoryItem[]
  overall_progress: number
}

export interface QuizHistoryItem {
  topic_id: string
  score: number
  correct_count: number
  total_questions: number
  created_at: string
}