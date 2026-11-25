import React from 'react'

export function Card({ children, className = '', ...rest }) {
  return <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`} {...rest}>{children}</div>
}

export function SectionTitle({ children, right, className = '' }) {
  return (
    <div className={`flex items-center justify-between mb-3 ${className}`}>
      <h3 className="text-sm font-semibold text-slate-800">{children}</h3>
      {right}
    </div>
  )
}

export function Badge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-600',
    blue: 'bg-brand-50 text-brand-700',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    red: 'bg-rose-50 text-rose-700',
    purple: 'bg-violet-50 text-violet-700',
  }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${tones[tone] || tones.slate}`}>{children}</span>
}

export function SeverityBadge({ severity }) {
  const map = {
    '심각': 'red', '위험': 'red', '주의': 'amber', '관심': 'blue', '정상': 'green',
    '높음': 'red', '보통': 'amber', '낮음': 'slate',
    'positive': 'green', 'negative': 'red', 'neutral': 'slate',
  }
  return <Badge tone={map[severity] || 'slate'}>{severity}</Badge>
}

export function SentimentBadge({ s }) {
  const map = { positive: ['긍정', 'green'], negative: ['부정', 'red'], neutral: ['중립', 'slate'] }
  const [label, tone] = map[s] || [s, 'slate']
  return <Badge tone={tone}>{label}</Badge>
}

export function Stat({ label, value, sub, tone = 'slate' }) {
  const tones = {
    slate: 'text-slate-900', green: 'text-emerald-600', red: 'text-rose-600',
    amber: 'text-amber-600', blue: 'text-brand-600',
  }
  return (
    <Card className="p-4">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`text-xl font-bold ${tones[tone] || tones.slate}`}>{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </Card>
  )
}

export function EmptyState({ title = '데이터가 없습니다', desc = '' }) {
  return (
    <div className="py-10 text-center">
      <div className="text-slate-400 text-sm">{title}</div>
      {desc && <div className="text-slate-400 text-xs mt-1">{desc}</div>}
    </div>
  )
}

export function Loading() {
  return <div className="py-10 text-center text-slate-400 text-sm">불러오는 중…</div>
}

export function ErrorBox({ error }) {
  if (!error) return null
  return <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-lg px-4 py-3 text-sm my-3">{error}</div>
}

export function DemoTag() {
  return <Badge tone="purple">데모 데이터</Badge>
}

// 렌더링 오류가 나도 화면 전체가 하얗게 죽지 않도록 하는 에러 경계
export class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(error) { return { error } }
  render() {
    if (this.state.error) {
      return (
        <div className="m-6 bg-rose-50 border border-rose-200 rounded-xl p-6">
          <div className="font-semibold text-rose-700 mb-1">화면 표시 중 오류가 발생했습니다</div>
          <div className="text-sm text-rose-600">{String(this.state.error)}</div>
          <button onClick={() => { this.setState({ error: null }); window.location.reload() }}
            className="mt-3 text-xs border border-rose-300 rounded-lg px-3 py-1.5 text-rose-700 hover:bg-rose-100">
            새로고침
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
