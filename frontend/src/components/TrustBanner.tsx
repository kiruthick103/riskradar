import React from "react";
import { ShieldAlert, Info, Sparkles, CheckCircle2 } from "lucide-react";

interface TrustBannerProps {
  tenantName: string;
  isBackendConnected: boolean;
  onOpenEvaluation?: () => void;
}

export const TrustBanner: React.FC<TrustBannerProps> = ({
  tenantName,
  isBackendConnected,
  onOpenEvaluation
}) => {
  return (
    <div className="bg-gradient-to-r from-amber-500/10 via-slate-900/40 to-cyan-500/10 border-b border-amber-500/20 px-4 py-2 text-xs backdrop-blur-md">
      <div className="max-w-[1720px] mx-auto flex flex-wrap items-center justify-between gap-2 text-slate-300">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <ShieldAlert className="w-3.5 h-3.5" />
          </div>
          <span className="font-semibold text-amber-300 tracking-wide uppercase text-[11px]">
            Trust & Governance Advisory:
          </span>
          <span className="text-slate-200">
            Decision-support system, not an autonomous safety authority. All high-potential precursor determinations require qualified HSE human review.
          </span>
        </div>

        <div className="flex items-center gap-3 text-[11px]">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Tenant: <strong className="text-amber-300">{tenantName}</strong>
          </span>

          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-slate-300">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            Dataset: <span className="text-slate-300">Synthetic Prototype Data (N=250)</span>
          </span>

          {onOpenEvaluation && (
            <button
              onClick={onOpenEvaluation}
              className="text-cyan-400 hover:text-cyan-300 underline font-medium cursor-pointer transition"
            >
              View Model Evaluation & F2 Metric ?
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
