export const Card = ({ title, actions, children, className = '' }) => <section className={`rounded-xl border border-slate-200 bg-white p-5 ${className}`}>
  {(title || actions) && <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
    {title && <h3 className="font-display text-base font-semibold text-slate-900">{title}</h3>}{actions}
  </div>}
  {children}
</section>;

export const Button = ({ variant = 'primary', className = '', ...props }) => <button type="button" {...props}
  className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variant === 'primary'
    ? 'bg-blue-600 text-white hover:bg-blue-700' : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'} ${className}`} />;

export const Field = ({ label, hint, ...props }) => <label className="block text-sm">
  <span className="mb-1 block font-medium text-slate-700">{label}</span>
  <input {...props} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-600 focus:outline-none" />
  {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
</label>;

export const Alert = ({ tone = 'error', children }) => children ? <p role={tone === 'error' ? 'alert' : 'status'}
  className={`rounded-lg px-3 py-2 text-sm ${tone === 'error' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>{children}</p> : null;

const BADGE = {
  opportunity: 'bg-emerald-100 text-emerald-800', risk: 'bg-red-100 text-red-800', change: 'bg-sky-100 text-sky-800',
  PENDING: 'bg-slate-100 text-slate-700', APPROVED: 'bg-emerald-100 text-emerald-800', ON_HOLD: 'bg-amber-100 text-amber-800',
  REJECTED: 'bg-red-100 text-red-800', OPEN: 'bg-slate-100 text-slate-700', IN_PROGRESS: 'bg-sky-100 text-sky-800', DONE: 'bg-emerald-100 text-emerald-800',
};
export const LABEL = {
  opportunity: '기회', risk: '위험', change: '변화', PENDING: '검토 대기', APPROVED: '승인', ON_HOLD: '보류', REJECTED: '반려',
  OPEN: '대기', IN_PROGRESS: '진행 중', DONE: '완료', high: '높음', medium: '중간', low: '낮음',
};
export const Badge = ({ value }) => <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${BADGE[value] || 'bg-slate-100 text-slate-700'}`}>{LABEL[value] || value}</span>;
