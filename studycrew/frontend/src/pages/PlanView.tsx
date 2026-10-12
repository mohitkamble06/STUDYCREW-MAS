import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Calendar, Clock, AlertTriangle, Loader2, BarChart2, RefreshCw } from 'lucide-react'
import { progressApi, runsApi } from '@/lib/api'
import { useSSE } from '@/hooks/useSSE'
import { cn, formatDate, formatMinutes, getActivityColor, getActivityIcon } from '@/lib/utils'
import { LiveAgentFeed } from '@/components/LiveAgentFeed'

export function PlanView() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const [plan, setPlan] = useState<StudyPlan | null>(null)
  const [runId, setRunId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isExecuting, setIsExecuting] = useState(false)
  const [error, setError] = useState('')
  const { events, isConnected, clearEvents } = useSSE(runId)

  useEffect(() => {
    if (courseId) {
      loadPlan()
    }
  }, [courseId])

  const loadPlan = async () => {
    try {
      const data = await progressApi.getPlan(courseId!)
      setPlan(data)
    } catch (err) {
      // No plan yet, try to start a run
      try {
        const run = await runsApi.create({ course_id: courseId! })
        setRunId(run.id)
        await executeRun(run.id)
      } catch (e) {
        setError('Failed to load or create plan')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const executeRun = async (id: string) => {
    setIsExecuting(true)
    clearEvents()
    try {
      await runsApi.execute(id)
    } catch (err) {
      setError('Failed to start crew execution')
      setIsExecuting(false)
    }
  }

  const handleReplan = async () => {
    try {
      setIsExecuting(true)
      const newPlan = await progressApi.replan(courseId!)
      setPlan(newPlan)
    } catch (err) {
      setError('Failed to regenerate plan')
    } finally {
      setIsExecuting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-900">No Plan Yet</h3>
        <p className="text-slate-600 mt-1">The crew is still working on your plan...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Study Plan</h2>
          <p className="text-slate-600 mt-1">
            {plan.total_days} days · {formatMinutes(plan.total_minutes)} total · {plan.days.length} scheduled days
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to={`/dashboard/${courseId}`} className="btn-secondary">
            <BarChart2 className="h-4 w-4" />
            Dashboard
          </Link>
          <button onClick={handleReplan} disabled={isExecuting} className="btn-primary">
            <RefreshCw className={cn('h-4 w-4', isExecuting && 'animate-spin')} />
            Re-plan
          </button>
        </div>
      </div>

      {/* Warnings */}
      {plan.warnings.length > 0 && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
          <h4 className="font-medium text-amber-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> Notes
          </h4>
          <ul className="mt-2 space-y-1 text-sm text-amber-700">
            {plan.warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-0.5">•</span>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* SSE Status */}
      {runId && (
        <div className={cn('rounded-lg p-3 text-sm flex items-center gap-2', isConnected ? 'bg-green-50 text-green-800' : 'bg-slate-50 text-slate-600')}>
          <span className={cn('h-2 w-2 rounded-full', isConnected ? 'bg-green-500' : 'bg-slate-400')} />
          {isConnected ? 'Agents working live...' : 'Waiting for agent updates...'}
          {events.length > 0 && (
            <span className="ml-auto text-xs bg-slate-200 px-2 py-0.5 rounded">
              {events.length} events
            </span>
          )}
        </div>
      )}

      {/* Plan Days */}
      <div className="space-y-4">
        {plan.days.map((day, dayIndex) => (
          <DayCard key={dayIndex} day={day} dayIndex={dayIndex} courseId={courseId!} />
        ))}
      </div>

      {plan.warnings.some(w => w.includes('not fit') || w.includes('prioritize')) && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
          <p className="text-blue-800 text-sm">
            <strong>Tip:</strong> Some topics may not fit in the available time. Consider increasing hours per day,
            extending the timeline, or reducing topic scope.
          </p>
        </div>
      )}
    </div>
  )
}

interface DayCardProps {
  day: DayPlan
  dayIndex: number
  courseId: string
}

function DayCard({ day, dayIndex, courseId }: DayCardProps) {
  const isPast = new Date(day.date) < new Date()
  const isToday = new Date(day.date).toDateString() === new Date().toDateString()

  return (
    <div className={cn('card p-5', isPast && 'opacity-60', isToday && 'ring-2 ring-primary-500')}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={cn(
            'flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold',
            isToday ? 'bg-primary-100 text-primary-700' : 'bg-slate-100 text-slate-600'
          )}>
            {dayIndex + 1}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-900">{formatDate(day.date)}</span>
              {isToday && <span className="badge bg-primary-100 text-primary-700">Today</span>}
              {isPast && <span className="badge bg-slate-100 text-slate-600">Done</span>}
            </div>
            <p className="text-sm text-slate-500">{day.reason}</p>
          </div>
        </div>

        <div className="flex items-center gap-4 sm:ml-auto">
          <span className={cn('badge', getActivityColor(day.activity))}>
            {getActivityIcon(day.activity)} {day.activity.replace('_', ' ')}
          </span>
          <span className="text-sm text-slate-500 flex items-center gap-1">
            <Clock className="h-4 w-4" />
            {formatMinutes(day.minutes)}
          </span>
        </div>
      </div>

      {day.topics.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {day.topics.map((topicId: string) => (
            <Link
              key={topicId}
              to={`/topic/${topicId}`}
              className="btn-secondary text-sm hover:bg-primary-50 hover:text-primary-700"
            >
              {topicId.slice(0, 8)}...
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

// Import types
import type { StudyPlan, DayPlan } from '@/lib/api'