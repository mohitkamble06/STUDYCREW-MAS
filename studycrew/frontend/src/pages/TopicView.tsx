import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Loader2, HelpCircle, MessageSquare, Send, BookOpen, Lightbulb } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { topicsApi } from '@/lib/api'
import { cn, formatDate } from '@/lib/utils'

export function TopicView() {
  const { topicId } = useParams<{ topicId: string }>()
  const [topic, setTopic] = useState<TopicData | null>(null)
  const [notes, setNotes] = useState<TopicNotes | null>(null)
  const [explanation, setExplanation] = useState<Explanation | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'notes' | 'explanation'>('explanation')
  const [followUpQuestion, setFollowUpQuestion] = useState('')
  const [followUpAnswer, setFollowUpAnswer] = useState<string | null>(null)
  const [isAsking, setIsAsking] = useState(false)

  useEffect(() => {
    if (topicId) {
      loadTopic()
    }
  }, [topicId])

  const loadTopic = async () => {
    try {
      const [topicData, content] = await Promise.all([
        topicsApi.get(topicId!),
        topicsApi.getContent(topicId!),
      ])
      setTopic(topicData)
      setNotes(content.notes)
      setExplanation(content.explanation)
    } catch (err) {
      console.error('Failed to load topic:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!followUpQuestion.trim() || isAsking) return

    setIsAsking(true)
    try {
      const response = await topicsApi.askFollowUp(topicId!, followUpQuestion.trim())
      setFollowUpAnswer(response.answer)
      setFollowUpQuestion('')
    } catch (err) {
      console.error('Failed to ask follow-up:', err)
    } finally {
      setIsAsking(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (!topic || !notes || !explanation) {
    return (
      <div className="text-center py-12">
        <HelpCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-900">Content Not Found</h3>
        <p className="text-slate-600 mt-1">Run the crew first to generate notes and explanations.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to={`/plan/${topic.course_id}`} className="btn-ghost p-2">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{topic.name}</h2>
          <div className="flex items-center gap-4 mt-1 text-sm text-slate-600">
            <span className="flex items-center gap-1">
              <BookOpen className="h-4 w-4" /> Importance: {topic.importance}/3
            </span>
            <span className="flex items-center gap-1">
              <Lightbulb className="h-4 w-4" /> Mastery: {Math.round(topic.mastery * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="card">
        <div className="border-b border-slate-200">
          <nav className="flex gap-4" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('notes')}
              className={cn(
                'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === 'notes'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              )}
            >
              Notes
            </button>
            <button
              onClick={() => setActiveTab('explanation')}
              className={cn(
                'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === 'explanation'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              )}
            >
              Explanation
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'notes' && <NotesView notes={notes} />}
          {activeTab === 'explanation' && <ExplanationView explanation={explanation} />}
        </div>
      </div>

      {/* Follow-up Question */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2 mb-4">
          <MessageSquare className="h-5 w-5" /> Ask a Follow-up Question
        </h3>

        {followUpAnswer && (
          <div className="mb-4 p-4 bg-primary-50 border border-primary-200 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                <Lightbulb className="h-4 w-4 text-primary-600" />
              </div>
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{followUpAnswer}</ReactMarkdown>
              </div>
            </div>
            <button
              onClick={() => setFollowUpAnswer(null)}
              className="mt-2 text-sm text-primary-600 hover:underline"
            >
              Ask another question
            </button>
          </div>
        )}

        <form onSubmit={handleAsk} className="flex gap-3">
          <input
            type="text"
            value={followUpQuestion}
            onChange={e => setFollowUpQuestion(e.target.value)}
            placeholder="e.g., Can you explain the difference between 2NF and 3NF with an example?"
            className="input flex-1"
            disabled={isAsking}
          />
          <button
            type="submit"
            disabled={isAsking || !followUpQuestion.trim()}
            className="btn-primary"
          >
            {isAsking ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Asking...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Ask
              </>
            )}
          </button>
        </form>

        <p className="mt-2 text-xs text-slate-500">
          Questions are answered based on the topic notes and your conversation history.
        </p>
      </div>
    </div>
  )
}

function NotesView({ notes }: { notes: TopicNotes }) {
  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-sm font-semibold text-slate-900 mb-2">Summary</h4>
        <p className="text-slate-700">{notes.summary}</p>
      </div>

      {notes.key_points.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-900 mb-2">Key Points</h4>
          <ul className="space-y-1">
            {notes.key_points.map((point, i) => (
              <li key={i} className="text-slate-700 flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400 flex-shrink-0" />
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}

      {notes.definitions.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-900 mb-2">Definitions</h4>
          <dl className="space-y-3">
            {notes.definitions.map((def, i) => (
              <div key={i} className="p-3 bg-slate-50 rounded-lg">
                <p className="text-slate-700">{def}</p>
              </div>
            ))}
          </dl>
        </div>
      )}

      {notes.formulas_or_examples.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-900 mb-2">Formulas & Examples</h4>
          <div className="space-y-3">
            {notes.formulas_or_examples.map((item, i) => (
              <div key={i} className="p-3 bg-slate-50 rounded-lg font-mono text-sm text-slate-700">
                {item}
              </div>
            ))}
          </div>
        </div>
      )}

      {notes.sources.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-900 mb-2">Sources</h4>
          <ul className="space-y-2 text-sm">
            {notes.sources.map((source, i) => (
              <li key={i} className="text-slate-600 flex items-start gap-2">
                <span className="mt-0.5">•</span>
                <span className="font-medium capitalize">{source.type.replace('_', ' ')}</span>
                {source.doc_id && <span className="text-slate-400">doc: {source.doc_id.slice(0, 8)}...</span>}
                {source.excerpt && <span className="text-slate-500 italic">"{source.excerpt.slice(0, 100)}..."</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function ExplanationView({ explanation }: { explanation: Explanation }) {
  return (
    <div className="space-y-6">
      <div className="prose prose-slate max-w-none">
        <ReactMarkdown>{explanation.explanation_markdown}</ReactMarkdown>
      </div>

      {explanation.example && (
        <div className="p-4 bg-primary-50 border border-primary-200 rounded-lg">
          <h4 className="text-sm font-semibold text-primary-900 mb-2 flex items-center gap-2">
            <Lightbulb className="h-4 w-4" /> Example
          </h4>
          <p className="text-primary-800">{explanation.example}</p>
        </div>
      )}

      {explanation.common_mistakes.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-slate-900 mb-2 flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-amber-600" /> Common Mistakes
          </h4>
          <ul className="space-y-1">
            {explanation.common_mistakes.map((mistake, i) => (
              <li key={i} className="text-slate-700 flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                {mistake}
              </li>
            ))}
          </ul>
        </div>
      )}

      {explanation.check_question && (
        <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
          <h4 className="text-sm font-semibold text-slate-900 mb-2">Check Your Understanding</h4>
          <p className="text-slate-700 italic">"{explanation.check_question}"</p>
        </div>
      )}
    </div>
  )
}

// Types
interface TopicData {
  id: string
  course_id: string
  name: string
  importance: number
  mastery: number
}

interface TopicNotes {
  topic: string
  summary: string
  key_points: string[]
  definitions: string[]
  formulas_or_examples: string[]
  sources: SourceRef[]
}

interface SourceRef {
  type: 'uploaded' | 'model_knowledge'
  doc_id: string | null
  chunk_id: string | null
  excerpt: string
}

interface Explanation {
  explanation_markdown: string
  example: string
  common_mistakes: string[]
  check_question: string
}