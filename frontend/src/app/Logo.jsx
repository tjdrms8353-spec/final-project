export function Logo({ className = '', light = false }) {
  return <span className={`inline-flex items-center gap-2 ${className}`}>
    <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#4f46e5" />
      <path d="M9 21c3-8 5-11 7-11s4 3 7 11" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M12 23l4-5 4 5" fill="none" stroke="#f43f5e" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <span className={`text-lg font-bold tracking-tight ${light ? 'text-white' : 'text-slate-900'}`}>dayribbon</span>
  </span>;
}
