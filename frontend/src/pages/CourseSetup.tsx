import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Minus, FileText, Upload, Loader2 } from 'lucide-react'
import { coursesApi, uploadsApi } from '@/lib/api'
import { cn } from '@/lib/utils'

interface TopicInput {
  id: string
  name: string
  importance: number
}

export function CourseSetup() {
  const navigate = useNavigate()
  const [subject, setSubject] = useState('')
  const [examDate, setExamDate] = useState('')
  const [hoursPerDay, setHoursPerDay] = useState(2)
  const [level, setLevel] = useState<'beginner' | 'intermediate' | 'advanced'>('beginner')
  const [topics, setTopics] = useState<TopicInput[]>([{ id: '1', name: '', importance: 1 }])
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})

  const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0]

  const addTopic = () => {
    setTopics([...topics, { id: Date.now().toString(), name: '', importance: 1 }])
  }

  const removeTopic = (id: string) => {
    if (topics.length <= 1) return
    setTopics(topics.filter(t => t.id !== id))
  }

  const updateTopic = (id: string, field: 'name' | 'importance', value: string | number) => {
    setTopics(topics.map(t => t.id === id ? { ...t, [field]: value } : t))
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setUploadedFiles(prev => [...prev, ...files])
    e.target.value = ''
  }

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    // Validate
    const validTopics = topics.filter(t => t.name.trim())
    if (!subject.trim()) {
      setError('Subject is required')
      setIsSubmitting(false)
      return
    }
    if (!examDate) {
      setError('Exam date is required')
      setIsSubmitting(false)
      return
    }
    if (validTopics.length === 0) {
      setError('At least one topic is required')
      setIsSubmitting(false)
      return
    }

    try {
      // Create course
      const course = await coursesApi.create({
        subject: subject.trim(),
        exam_date: examDate,
        hours_per_day: hoursPerDay,
        level,
        topics: validTopics.map(t => ({ name: t.name.trim(), importance: t.importance })),
      })

      // Upload files if any
      for (let i = 0; i < uploadedFiles.length; i++) {
        const file = uploadedFiles[i]
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }))
        try {
          await uploadsApi.upload(course.id, file)
          setUploadProgress(prev => ({ ...prev, [file.name]: 100 }))
        } catch (err) {
          console.error('Upload failed:', err)
        }
      }

      navigate(`/plan/${course.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create course')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-slate-900">Build Your Study Crew</h2>
        <p className="mt-2 text-slate-600">
          Enter your exam details and topics. Our AI agents will create a personalized study plan.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="card p-6 space-y-6">
          <h3 className="text-lg font-semibold text-slate-900">Course Details</h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={e => setSubject(e.target.value)}
                placeholder="e.g., Database Management Systems"
                className="input"
                required
              />
            </div>

            <div>
              <label className="label">Exam Date</label>
              <input
                type="date"
                value={examDate}
                onChange={e => setExamDate(e.target.value)}
                min={tomorrow}
                className="input"
                required
              />
            </div>

            <div>
              <label className="label">Hours per Day</label>
              <input
                type="number"
                value={hoursPerDay}
                onChange={e => setHoursPerDay(Number(e.target.value))}
                min={0.5}
                max={12}
                step={0.5}
                className="input"
                required
              />
            </div>

            <div>
              <label className="label">Your Level</label>
              <select
                value={level}
                onChange={e => setLevel(e.target.value as typeof level)}
                className="input"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
          </div>
        </div>

        <div className="card p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-900">Topics</h3>
            <button type="button" onClick={addTopic} className="btn-secondary text-sm">
              <Plus className="h-4 w-4" /> Add Topic
            </button>
          </div>

          <div className="space-y-3">
            {topics.map((topic, index) => (
              <div key={topic.id} className="flex items-center gap-3">
                <span className="text-slate-500 w-6 text-center">{index + 1}.</span>
                <input
                  type="text"
                  value={topic.name}
                  onChange={e => updateTopic(topic.id, 'name', e.target.value)}
                  placeholder={`Topic ${index + 1}`}
                  className="input flex-1"
                />
                <select
                  value={topic.importance}
                  onChange={e => updateTopic(topic.id, 'importance', Number(e.target.value))}
                  className="input w-32"
                >
                  <option value={1}>Low (1)</option>
                  <option value={2}>Medium (2)</option>
                  <option value={3}>High (3)</option>
                </select>
                <button
                  type="button"
                  onClick={() => removeTopic(topic.id)}
                  disabled={topics.length <= 1}
                  className={cn(
                    'p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors',
                    topics.length <= 1 && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  <Minus className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <FileText className="h-5 w-5" /> Study Materials (Optional)
          </h3>
          <p className="text-sm text-slate-600">
            Upload notes, syllabus, or reference materials (PDF, TXT, MD). Agents will use these for research.
          </p>

          <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center">
            <input
              type="file"
              multiple
              accept=".pdf,.txt,.md"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <Upload className="h-10 w-10 mx-auto text-slate-400 mb-2" />
              <p className="text-slate-600">Click to upload or drag and drop</p>
              <p className="text-xs text-slate-400 mt-1">PDF, TXT, MD files</p>
            </label>
          </div>

          {uploadedFiles.length > 0 && (
            <div className="space-y-2">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-slate-500" />
                    <div>
                      <p className="text-sm font-medium text-slate-900">{file.name}</p>
                      <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="text-slate-400 hover:text-red-500"
                  >
                    <span className="sr-only">Remove</span>
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary w-full py-3 text-lg"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Building your crew plan...
            </>
          ) : (
            'Build My Crew Plan'
          )}
        </button>
      </form>
    </div>
  )
}