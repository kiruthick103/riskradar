import React, { useState } from "react";
import { X, Send, Bot, Sparkles, Shield, AlertTriangle, ArrowRight, CornerDownLeft, Loader2, CheckCircle2 } from "lucide-react";
import { askAIAssistant } from "../api/client";
import { ReportItem } from "../types";

interface AIAssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  tenantName: string;
  tenantId: string;
  onSelectReport: (reportId: string) => void;
}

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  citations?: Array<{
    report_id: string;
    external_ref: string;
    site: string;
    date: string;
    activity: string;
    sif_potential_label: string;
    narrative_excerpt: string;
  }>;
  groundedCount?: number;
  timestamp: string;
}

const SUGGESTED_QUERIES = [
  "Which sites had isolation failures this month?",
  "Show me high SIF precursors in lifting operations",
  "What barrier failures are trending across Duliajan?",
  "List unverified permit to work observations"
];

export const AIAssistantDrawer: React.FC<AIAssistantDrawerProps> = ({
  isOpen,
  onClose,
  tenantName,
  tenantId,
  onSelectReport
}) => {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: `Hello! I am your RiskRadar AI Safety Assistant for ${tenantName}. I answer safety intelligence questions grounded strictly in the verified safety observation database with exact report citations. How can I assist your HSE team today?`,
      timestamp: "Just now"
    }
  ]);

  if (!isOpen) return null;

  const handleSend = async (textToSend?: string) => {
    const q = (textToSend || query).trim();
    if (!q || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setIsLoading(true);

    try {
      const res = await askAIAssistant(q, tenantId);
      const assistantMsg: Message = {
        id: `ai-${Date.now()}`,
        sender: "assistant",
        text: res.response || "No response received.",
        citations: res.citations || [],
        groundedCount: res.grounded_report_count || 0,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `ai-err-${Date.now()}`,
          sender: "assistant",
          text: "I encountered an error querying the safety database. Please try again with different keywords.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
      <div className="w-full max-w-xl h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col text-slate-100 animate-in slide-in-from-right duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-md shadow-cyan-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide">RiskRadar AI Assistant</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Grounded RAG
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                Grounded in <strong className="text-slate-300">{tenantName}</strong> report database
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Suggested Queries */}
        <div className="px-6 py-3 bg-slate-950/40 border-b border-slate-800/80">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
            Suggested HSE Investigations
          </span>
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTED_QUERIES.map((sq, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(sq)}
                className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 text-slate-300 hover:text-white transition cursor-pointer text-left"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[90%] rounded-2xl p-4 text-xs leading-relaxed ${
                  m.sender === "user"
                    ? "bg-blue-600 text-white rounded-br-none shadow-md shadow-blue-600/10 font-medium"
                    : "bg-slate-800/90 text-slate-200 border border-slate-700/70 rounded-bl-none"
                }`}
              >
                {m.sender === "assistant" && (
                  <div className="flex items-center gap-1.5 mb-2 text-cyan-400 font-semibold text-[11px]">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Safety Intelligence Synthesis</span>
                  </div>
                )}
                <div className="whitespace-pre-wrap">{m.text}</div>

                {/* Grounded Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-700/60 space-y-2">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">
                      Cited Verified Safety Observations ({m.citations.length})
                    </span>
                    <div className="space-y-1.5">
                      {m.citations.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-700/50 hover:border-slate-600 transition flex items-center justify-between gap-2"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-[11px] font-bold text-amber-300">
                                {c.external_ref}
                              </span>
                              <span
                                className={`text-[9px] px-1.5 py-0.2 rounded-full font-bold ${
                                  c.sif_potential_label === "HIGH"
                                    ? "bg-red-500/20 text-red-400 border border-red-500/30"
                                    : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                }`}
                              >
                                {c.sif_potential_label} SIF
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-400 truncate mt-0.5">
                              {c.site} ? {c.activity}
                            </div>
                          </div>
                          <button
                            onClick={() => {
                              onSelectReport(c.report_id);
                              onClose();
                            }}
                            className="px-2.5 py-1 text-[10px] font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-400 rounded-md border border-slate-700/70 hover:text-cyan-300 transition flex items-center gap-1 shrink-0 cursor-pointer"
                          >
                            <span>Inspect</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <span className="text-[9px] text-slate-500 mt-1 px-1">{m.timestamp}</span>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
              <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
              <span>Synthesizing answer grounded in verified reports...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask HSE question (e.g. which sites had isolation failures?)..."
              className="flex-1 bg-slate-800/90 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-cyan-500 transition"
            />
            <button
              type="submit"
              disabled={!query.trim() || isLoading}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center gap-1.5 transition cursor-pointer shadow-md shadow-cyan-500/20"
            >
              <span>Ask</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
          <p className="text-[10px] text-slate-500 text-center mt-2">
            Answers are strictly grounded in retrieved reports with citations. No fabricated observations.
          </p>
        </div>

      </div>
    </div>
  );
};
