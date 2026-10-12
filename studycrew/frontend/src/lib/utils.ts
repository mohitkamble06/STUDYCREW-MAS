import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatMinutes(minutes: number): string {
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  }
  return `${minutes}m`
}

export function getActivityColor(activity: string): string {
  switch (activity) {
    case 'learn':
      return 'bg-blue-100 text-blue-800'
    case 'revise':
      return 'bg-green-100 text-green-800'
    case 'practice':
      return 'bg-orange-100 text-orange-800'
    case 'mock_test':
      return 'bg-purple-100 text-purple-800'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

export function getActivityIcon(activity: string): string {
  switch (activity) {
    case 'learn':
      return '📚'
    case 'revise':
      return '🔁'
    case 'practice':
      return '✏️'
    case 'mock_test':
      return '🧪'
    default:
      return '📝'
  }
}

export function getMasteryColor(mastery: number): string {
  if (mastery >= 0.8) return 'bg-green-500'
  if (mastery >= 0.6) return 'bg-lime-500'
  if (mastery >= 0.4) return 'bg-yellow-500'
  if (mastery >= 0.2) return 'bg-orange-500'
  return 'bg-red-500'
}

export function getMasteryLabel(mastery: number): string {
  if (mastery >= 0.8) return 'Strong'
  if (mastery >= 0.6) return 'Good'
  if (mastery >= 0.4) return 'Fair'
  if (mastery >= 0.2) return 'Weak'
  return 'New'
}