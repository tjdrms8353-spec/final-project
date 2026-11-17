import React from 'react';
import { AlertTriangle, CheckCircle2, X } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';

export const ValidationToasts: React.FC = () => {
  const { toasts, dismissToast } = usePlatform();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2.5 w-full max-w-sm px-4 sm:px-0 pointer-events-none"
    >
      {toasts.map((toast) => {
        const isPassed = toast.status === 'PASSED';
        return (
          <div
            key={toast.id}
            className={`pointer-events-auto bg-white border rounded-lg shadow-md p-3.5 flex items-start gap-3 transition-transform ${
              isPassed ? 'border-slate-200' : 'border-red-300'
            }`}
          >
            {isPassed ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            )}

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono font-semibold text-slate-800">
                  {toast.guardRule}
                </span>
                <span aria-hidden="true" className="text-slate-300">
                  ·
                </span>
                <span
                  className={`font-semibold ${
                    isPassed ? 'text-emerald-700' : 'text-red-700'
                  }`}
                >
                  {isPassed ? '검증 통과' : '요청 차단'}
                </span>
              </div>
              <p className="text-xs font-semibold text-slate-900 mt-0.5 truncate">
                {toast.title}
              </p>
              <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                {toast.message}
              </p>
            </div>

            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              aria-label="알림 닫기"
              className="text-slate-400 hover:text-slate-600 p-0.5 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
