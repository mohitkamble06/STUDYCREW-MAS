import { useEffect, useState } from 'react'
import { X, CheckCircle, AlertCircle, Loader2, Bot, Brain, BookOpen, HelpCircle, Trophy, TrendingUp } from 'lucide-react'
import { useSSE } from '@/hooks/useSSE'
import { cn, formatDateTime } from '@/lib/utils'

// This component shows live agent activity from any active run
// In a real app, you'd track the current run ID from context/state

export function LiveAgentFeed() {
  // For demo purposes, we'll show a placeholder
  // In reality, this would connect to the active run's SSE stream
  const [isVisible, setIsVisible] = useState(false)
  const [events, setEvents] = useState<AgentEvent[]>([])

  // This would be replaced with actual run ID from context
  const runId = ''

  if (!isVisible || !runId) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-h-96 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden">
      <div className="flex items-center justify-between p-3 border-b border-slate-200 bg-slate-50">
        <h3 className="font-semibold text-slate-900 flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary-600" />
          Live Agent Feed
        </h3>
        <button onClick={() => setIsVisible(false)} className="p-1 text-slate-400 hover:text-slate-600">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="max-h-[400px] overflow-y-auto p-3 space-y-2">
        {events.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">Waiting for agent activity...</p>
        ) : (
          events.slice().reverse().map((event, index) => (
            <AgentEventItem key={index} event={event} />
          ))
        )}
      </div>
    </div>
  )
}

function AgentEventItem({ event }: { event: AgentEvent }) {
  const agentIcons: Record<string, React.ReactNode> = {
    planner: <BookOpen className="h-4 w-4" />,
    researcher: <Brain className="h-4 w-4" />,
    tutor: <HelpCircle className="h-4 w-4" />,
    quizzer: <Trophy className="h-4 w-4" />,
    tracker: <TrendingUp className="h-4 w-4" />,
    coordinator: <Bot className="h-4 w-4" />,
  }

  const agentColors: Record<string, string> = {
    planner: 'bg-blue-100 text-blue-700',
    researcher: 'bg-purple-100 text-purple-700',
    tutor: 'bg-green-100 text-green-700',
    quizzer: 'bg-orange-100 text-orange-700',
    tracker: 'bg-pink-100 text-pink-700',
    coordinator: 'bg-slate-100 text-slate-700',
  }

  const statusIcons = {
    started: <Loader2 className="h-4 w-4 animate-spin" />,
    done: <CheckCircle className="h-4 w-4" />,
    error: <AlertCircle className="h-4 w-4" />,
  }

  const statusColors = {
    started: 'text-primary-600',
    done: 'text-green-600',
    error: 'text-red-600',
  }

  const Icon = agentIcons[event.agent] || <Bot className="h-4 w-4" />
  const StatusIcon = statusIcons[event.status]

  return (
    <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
      <div className={cn('p-2 rounded-lg flex-shrink-0', agentColors[event.agent] || 'bg-slate-100 text-slate-700')}>
        {Icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-900 capitalize">{event.agent}</span>
          <span className={cn('text-xs', statusColors[event.status])} flex items-center gap-1>
            {StatusIcon}
            {event.status}
          </span>
          {event.topic_id && (
            <span className="text-xs text-slate-500 px-2 py-0.5 bg-slate-100 rounded">
              {event.topic_id.slice(0, 8)}...
            </span>
          )}
        </div>
        <p className="text-sm text-slate-600 mt-1">{event.message}</p>
        <p className="text-xs text-slate-400 mt-1">{formatDateTime(event.timestamp)}</p>
      </div>
    </div>
  )
}

interface AgentEvent {
  run_id: string
  agent: string
  status: 'started' | 'done' | 'error'
  message: string
  topic_id: string | null
  timestamp: string
  data: Record<string, unknown>
}