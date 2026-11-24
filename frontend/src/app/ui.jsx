import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { eok, formatKpi, won } from '../services/biApi';

export const kpiText = (value, unit) => unit === 'KRW' && value != null && Math.abs(value) >= 1e8 ? `${eok(value)}원` : formatKpi(value, unit);
export const kpiTitle = (value, unit) => unit === 'KRW' && value != null ? won(value) : undefined;

export const CHART = {
  brand: '#4f46e5', amber: '#f59e0b', slate: '#94a3b8', green: '#16a34a', red: '#dc2626', violet: '#7c3aed', grid: '#e5e7eb', axis: '#64748b',
};

export const cx = (...c) => c.filter(Boolean).join(' ');

export function Card({ title, subtitle, actions, children, className = '', bodyClassName = '' }) {
  return <section className={cx('min-w-0 rounded-xl border border-slate-200 bg-white', className)}>
    {(title || actions) && <header className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 px-5 py-3.5">
      <div className="min-w-0">
        {title && <h3 className="text-[15px] font-semibold text-slate-900">{title}</h3>}
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>}
    <div className={cx('p-5', bodyClassName)}>{children}</div>
  </section>;
}

const BTN = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700',
  secondary: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
};
export function Button({ variant = 'primary', size = 'md', icon: Icon, children, className = '', type = 'button', ...props }) {
  return <button type={type} {...props} className={cx('inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50',
    size === 'sm' ? 'px-2.5 py-1.5 text-xs' : 'px-3.5 py-2 text-sm', BTN[variant], className)}>
    {Icon && <Icon className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} aria-hidden="true" />}{children}
  </button>;
}

const inputCls = 'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100';
export function Field({ label, hint, as = 'input', children, className = '', ...props }) {
  const Tag = as;
  return <label className={cx('block text-sm', className)}>
    {label && <span className="mb-1.5 block font-medium text-slate-700">{label}</span>}
    <Tag {...props} className={inputCls}>{children}</Tag>
    {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
  </label>;
}

export function Alert({ tone = 'error', children }) {
  if (!children) return null;
  const cls = { error: 'border-red-200 bg-red-50 text-red-800', ok: 'border-emerald-200 bg-emerald-50 text-emerald-800', info: 'border-slate-200 bg-slate-50 text-slate-700', warn: 'border-amber-200 bg-amber-50 text-amber-900' }[tone];
  return <p role={tone === 'error' ? 'alert' : 'status'} className={cx('rounded-lg border px-3 py-2 text-sm', cls)}>{children}</p>;
}

export const LABEL = {
  opportunity: '기회', risk: '위험', change: '변화', PENDING: '검토 대기', APPROVED: '승인', ON_HOLD: '보류', REJECTED: '반려',
  OPEN: '대기', IN_PROGRESS: '진행 중', DONE: '완료', high: '높음', medium: '중간', low: '낮음',
  OWNER: '대표·소유자', APPROVER: '승인권자', ANALYST: '분석가', VIEWER: '조회자',
};
const BADGE = {
  opportunity: 'bg-emerald-50 text-emerald-700 ring-emerald-200', risk: 'bg-red-50 text-red-700 ring-red-200', change: 'bg-sky-50 text-sky-700 ring-sky-200',
  PENDING: 'bg-amber-50 text-amber-800 ring-amber-200', APPROVED: 'bg-emerald-50 text-emerald-700 ring-emerald-200', ON_HOLD: 'bg-slate-100 text-slate-700 ring-slate-200',
  REJECTED: 'bg-red-50 text-red-700 ring-red-200', OPEN: 'bg-slate-100 text-slate-700 ring-slate-200', IN_PROGRESS: 'bg-sky-50 text-sky-700 ring-sky-200',
  DONE: 'bg-emerald-50 text-emerald-700 ring-emerald-200', high: 'bg-red-50 text-red-700 ring-red-200', medium: 'bg-amber-50 text-amber-800 ring-amber-200',
  low: 'bg-slate-100 text-slate-600 ring-slate-200', OWNER: 'bg-brand-50 text-brand-700 ring-brand-200', APPROVER: 'bg-brand-50 text-brand-700 ring-brand-200',
  ANALYST: 'bg-slate-100 text-slate-700 ring-slate-200', VIEWER: 'bg-slate-100 text-slate-600 ring-slate-200',
};
export function Badge({ value, children, prefix }) {
  return <span className={cx('inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset', BADGE[value] || 'bg-slate-100 text-slate-700 ring-slate-200')}>
    {prefix}{children ?? LABEL[value] ?? value}</span>;
}

export function PageHeader({ title, description, actions }) {
  return <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
    <div className="min-w-0">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </div>;
}

export function Empty({ icon: Icon, title, description, action }) {
  return <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 px-6 py-10 text-center">
    {Icon && <Icon className="mb-3 h-8 w-8 text-slate-400" aria-hidden="true" />}
    <p className="text-sm font-medium text-slate-700">{title}</p>
    {description && <p className="mt-1 max-w-sm text-xs text-slate-500">{description}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>;
}

export function Delta({ value, previous, higherIsBetter = true, unit }) {
  if (value == null || previous == null) return <span className="text-xs text-slate-400">비교 데이터 없음</span>;
  const diff = value - previous;
  if (Math.abs(diff) < 1e-9) return <span className="inline-flex items-center gap-0.5 text-xs text-slate-500"><Minus className="h-3 w-3" />전월과 동일</span>;
  const good = (diff > 0) === higherIsBetter;
  const Icon = diff > 0 ? ArrowUpRight : ArrowDownRight;
  const text = unit === '%' ? `${Math.abs(diff).toFixed(2)}%p` : unit === 'KRW' ? `${(Math.abs(diff) / 1e8).toFixed(1)}억` : `${Math.abs(diff).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}${unit}`;
  return <span className={cx('inline-flex items-center gap-0.5 text-xs font-medium tabular-nums', good ? 'text-emerald-700' : 'text-red-700')}>
    <Icon className="h-3.5 w-3.5" aria-hidden="true" />{text}<span className="sr-only">{good ? '개선' : '악화'}</span></span>;
}

export function Stat({ label, value, unit, previous, higherIsBetter, hint }) {
  return <div className="min-w-0 rounded-xl border border-slate-200 bg-white p-4">
    <p className="text-xs font-medium text-slate-500">{label}</p>
    <p className="mt-1.5 text-xl font-bold tabular-nums text-slate-900" title={kpiTitle(value, unit)}>{kpiText(value, unit)}</p>
    <div className="mt-1 flex items-center gap-1.5"><Delta value={value} previous={previous} higherIsBetter={higherIsBetter} unit={unit} />
      {previous != null && <span className="text-xs text-slate-400">전월 대비</span>}</div>
    {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
  </div>;
}

export const Loading = ({ label = '불러오는 중...' }) => <div className="flex items-center gap-2 py-10 text-sm text-slate-500" role="status">
  <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />{label}</div>;

export const dateKo = (v) => v ? new Date(v).toLocaleDateString('ko-KR') : '-';
export const dateTimeKo = (v) => v ? new Date(v).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' }) : '-';
