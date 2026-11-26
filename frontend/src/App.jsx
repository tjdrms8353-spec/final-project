import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import News from './pages/News'
import Finance from './pages/Finance'
import InternalData from './pages/InternalData'
import Kpi from './pages/Kpi'
import AiAnalysis from './pages/AiAnalysis'
import Simulation from './pages/Simulation'
import Alerts from './pages/Alerts'
import Decisions from './pages/Decisions'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import AuditLog from './pages/AuditLog'
import Ops from './pages/Ops'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="h-screen flex items-center justify-center text-slate-400">로딩 중…</div>
  if (!user) return <Navigate to="/login" replace />
  if (!user.company_id) return <Navigate to="/onboarding" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/app" element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="news" element={<News />} />
        <Route path="finance" element={<Finance />} />
        <Route path="data" element={<InternalData />} />
        <Route path="kpi" element={<Kpi />} />
        <Route path="analysis" element={<AiAnalysis />} />
        <Route path="simulation" element={<Simulation />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="decisions" element={<Decisions />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
        <Route path="audit" element={<AuditLog />} />
        <Route path="ops" element={<Ops />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
