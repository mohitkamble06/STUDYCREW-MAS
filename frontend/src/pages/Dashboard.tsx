import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, TrendingUp, Clock, Trophy, RefreshCw, Loader2 } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  PieChart as RechartsPieChart,
} from 'recharts'
import { progressApi } from '@/lib/api'
import { cn, formatDate, getMasteryColor, getMasteryLabel } from '@/lib/utils'

export function Dashboard() {
  const { courseId } = useParams<{ courseId: string }>()
  const [progress, setProgress] = useState<ProgressSnapshot | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (courseId) {
      loadProgress()
    }
  }, [courseId])

  const loadProgress = async () => {
    try {
      const data = await progressApi.getProgress(courseId!)
      setProgress(data)
    } catch (err) {
      console.error('Failed to load progress:', err)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (!progress) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-600">No progress data available</p>
      </div>
    )
  }

  const masteryValues = Object.values(progress.topic_masteries)
  const avgMastery = masteryValues.length > 0
    ? masteryValues.reduce((a, b) => a + b, 0) / masteryValues.length
    : 0

  const totalQuizzes = progress.quiz_history.length
  const avgQuizScore = totalQuizzes > 0
    ? progress.quiz_history.reduce((a, b) => a + b.score, 0) / totalQuizzes
    : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to={`/plan/${courseId}`} className="btn-ghost p-2">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Progress Dashboard</h2>
          <p className="text-slate-600 mt-1">
            {progress.days_remaining} days until exam · {Math.round(avgMastery * 100)}% overall mastery
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Overall Mastery"
          value={`${Math.round(avgMastery * 100)}%`}
          icon={<TrendingUp className="h-6 w-6 text-green-600" />}
          trend={avgMastery >= 0.7 ? 'Strong' : avgMastery >= 0.4 ? 'Good progress' : 'Needs work'}
          trendColor={avgMastery >= 0.7 ? 'text-green-600' : avgMastery >= 0.4 ? 'text-yellow-600' : 'text-red-600'}
        />
        <StatCard
          title="Days Remaining"
          value={progress.days_remaining.toString()}
          icon={<Clock className="h-6 w-6 text-blue-600" />}
          trend={progress.days_remaining > 7 ? 'Plenty of time' : progress.days_remaining > 3 ? 'Getting close' : 'Final stretch!'}
          trendColor={progress.days_remaining > 7 ? 'text-green-600' : progress.days_remaining > 3 ? 'text-yellow-600' : 'text-red-600'}
        />
        <StatCard
          title="Quizzes Taken"
          value={totalQuizzes.toString()}
          icon={<Trophy className="h-6 w-6 text-purple-600" />}
          trend={totalQuizzes > 0 ? `${Math.round(avgQuizScore * 100)}% avg score` : 'No quizzes yet'}
          trendColor="text-slate-600"
        />
        <StatCard
          title="Completion"
          value={`${Math.round(progress.overall_progress * 100)}%`}
          icon={<RefreshCw className="h-6 w-6 text-orange-600" />}
          trend="Topics covered"
          trendColor="text-slate-600"
        />
      </div>

      {/* Mastery Chart */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Topic Mastery</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={masteryChartData(progress.topic_masteries)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" domain={[0, 1]} tickFormatter={v => `${Math.round(v * 100)}%`} />
              <YAxis type="category" dataKey="name" width={120} />
              <Tooltip formatter={(v: number) => [`${Math.round(v * 100)}%`, 'Mastery']} />
              <Bar dataKey="mastery" radius={[0, 4, 4, 0]}>
                {masteryChartData(progress.topic_masteries).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getMasteryColor(entry.mastery)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quiz History & Topic Details */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Quiz History</h3>
          {progress.quiz_history.length === 0 ? (
            <p className="text-slate-500 text-center py-8">No quizzes taken yet. Generate a quiz from a topic page!</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {progress.quiz_history.slice(0, 10).map((quiz, i) => (
                <QuizHistoryItem key={i} quiz={quiz} />
              ))}
            </div>
          )}
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Topic Details</h3>
          <div className="space-y-3">
            {Object.entries(progress.topic_masteries).map(([topicId, mastery]) => (
              <TopicMasteryRow key={topicId} topicId={topicId} mastery={mastery} courseId={courseId!} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon, trend, trendColor }: {
  title: string
  value: string
  icon: React.ReactNode
  trend: string
  trendColor: string
}) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-600">{title}</p>
          <p className="text-3xl font-bold text-slate-900 mt-1">{value}</p>
        </div>
        <div className="p-2 bg-slate-100 rounded-xl">{icon}</div>
      </div>
      <p className={cn('text-xs mt-3', trendColor)}>{trend}</p>
    </div>
  )
}

function QuizHistoryItem({ quiz }: { quiz: QuizHistoryItem }) {
  const scorePercent = Math.round(quiz.score * 100)
  return (
    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium text-white"
          style={{ backgroundColor: getMasteryColor(quiz.score) }}>
          {scorePercent}%
        </div>
        <div>
          <p className="text-sm font-medium text-slate-900">Topic {quiz.topic_id.slice(0, 8)}...</p>
          <p className="text-xs text-slate-500">{quiz.correct_count}/{quiz.total_questions} correct</p>
        </div>
      </div>
      <span className="text-xs text-slate-500">{formatDate(quiz.created_at)}</span>
    </div>
  )
}

function TopicMasteryRow({ topicId, mastery, courseId }: { topicId: string, mastery: number, courseId: string }) {
  return (
    <Link
      to={`/topic/${topicId}`}
      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
    >
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium text-white"
          style={{ backgroundColor: getMasteryColor(mastery) }}>
          {Math.round(mastery * 100)}%
        </div>
        <div>
          <p className="text-sm font-medium text-slate-900">Topic {topicId.slice(0, 8)}...</p>
          <p className="text-xs text-slate-500">{getMasteryLabel(mastery)} mastery</p>
        </div>
      </div>
    </Link>
  )
}

function masteryChartData(topicMasteries: Record<string, number>) {
  return Object.entries(topicMasteries).map(([topicId, mastery]) => ({
    name: `Topic ${topicId.slice(0, 6)}`,
    mastery,
  }))
}

interface ProgressSnapshot {
  course_id: string
  days_remaining: number
  topic_masteries: Record<string, number>
  quiz_history: QuizHistoryItem[]
  overall_progress: number
}

interface QuizHistoryItem {
  topic_id: string
  score: number
  correct_count: number
  total_questions: number
  created_at: string
}