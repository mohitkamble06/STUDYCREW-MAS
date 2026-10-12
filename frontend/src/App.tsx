import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { CourseSetup } from '@/pages/CourseSetup'
import { PlanView } from '@/pages/PlanView'
import { TopicView } from '@/pages/TopicView'
import { Dashboard } from '@/pages/Dashboard'
import { LiveAgentFeed } from '@/components/LiveAgentFeed'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <h1 className="text-xl font-bold text-slate-900">StudyCrew</h1>
              <nav className="flex items-center gap-4 text-sm text-slate-600">
                <span className="hidden sm:block">Multi-Agent Study Planner</span>
              </nav>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<CourseSetup />} />
            <Route path="/plan/:courseId" element={<PlanView />} />
            <Route path="/topic/:topicId" element={<TopicView />} />
            <Route path="/dashboard/:courseId" element={<Dashboard />} />
          </Routes>
        </main>

        {/* Global Live Agent Feed - shows when a run is active */}
        <LiveAgentFeed />
      </div>
    </BrowserRouter>
  )
}

export default App