import React, { useState, useRef, useEffect } from "react";
import { Globe, MoreHorizontal, Check, Building2, Bot, Sparkles, BarChart2, ChevronDown } from "lucide-react";
import { useLanguage, DROPDOWN_LANGUAGES, Language } from "../context/LanguageContext";

interface NavbarProps {
  activeScreen: number;
  setActiveScreen?: (s: number) => void;
  onOpenNewReportModal?: () => void;
  onOpenBatchModal?: () => void;
  onOpenVoiceModal?: () => void;
  totalReportsCount?: number;
  highSIFCount?: number;
  tenantId?: string;
  onSelectTenant?: (tenantId: string) => void;
  onOpenAIAssistant?: () => void;
}

const AVAILABLE_TENANTS = [
  { id: "oil_india", name: "Oil India Limited (OIL)", tag: "National Operator (Default)" },
  { id: "ongc", name: "ONGC (Offshore & Basin)", tag: "Extended MOC Rules" },
  { id: "global_ep", name: "Global E&P Contractors", tag: "Industry Standard Template" }
];

export const Navbar: React.FC<NavbarProps> = ({
  activeScreen,
  setActiveScreen,
  tenantId = "oil_india",
  onSelectTenant,
  onOpenAIAssistant
}) => {
  const { language, setLanguage, t } = useLanguage();
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false);
  const [isTenantMenuOpen, setIsTenantMenuOpen] = useState(false);

  const langDropdownRef = useRef<HTMLDivElement>(null);
  const tenantDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (langDropdownRef.current && !langDropdownRef.current.contains(event.target as Node)) {
        setIsLangMenuOpen(false);
      }
      if (tenantDropdownRef.current && !tenantDropdownRef.current.contains(event.target as Node)) {
        setIsTenantMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isDropdownActive = ["bn", "mr", "te", "ta"].includes(language);

  const getScreenTitle = (screenId: number): string => {
    switch (screenId) {
      case 1: return t("nav.dashboard");
      case 2: return t("nav.queue");
      case 3: return t("nav.ingest");
      case 4: return t("nav.chain");
      case 5: return t("nav.iogp");
      case 7: return t("nav.site");
      case 8: return t("nav.activity");
      case 9: return t("nav.barrier");
      case 10: return t("nav.telemetry");
      case 11: return t("nav.rca");
      case 12: return t("nav.detail");
      case 13: return "Model Evaluation & F2 Metric";
      default: return t("nav.dashboard");
    }
  };

  const currentTenant = AVAILABLE_TENANTS.find((t) => t.id === tenantId) || AVAILABLE_TENANTS[0];

  return (
    <header className="sticky top-0 z-20 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs px-6 sm:px-8 py-3">
      <div className="flex flex-wrap items-center justify-between gap-4 max-w-[1720px] mx-auto">
        {/* Active Screen Breadcrumb */}
        <div className="flex items-center gap-3">
          <h2 className="text-base sm:text-lg font-extrabold text-slate-900 m-0 tracking-tight">
            {getScreenTitle(activeScreen)}
          </h2>
          <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 font-mono font-bold">
            PS 26165 ? Team NorthStar
          </span>
        </div>

        {/* Right Panel Controls */}
        <div className="flex items-center gap-2.5 flex-wrap">
          
          {/* Ask AI Safety Assistant Button */}
          {onOpenAIAssistant && (
            <button
              type="button"
              onClick={onOpenAIAssistant}
              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs flex items-center gap-2 shadow-xs transition cursor-pointer"
            >
              <Bot className="w-3.5 h-3.5" />
              <span>AI Safety Assistant</span>
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
            </button>
          )}

          {/* Model Evaluation Link Button */}
          {setActiveScreen && (
            <button
              type="button"
              onClick={() => setActiveScreen(13)}
              className={`px-3 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1.5 border transition cursor-pointer ${
                activeScreen === 13
                  ? "bg-slate-900 text-white border-slate-900 shadow-xs"
                  : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200"
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5 text-cyan-500" />
              <span>Evaluation (F2)</span>
            </button>
          )}

          {/* Tenant / Company Switcher Dropdown */}
          <div className="relative" ref={tenantDropdownRef}>
            <button
              type="button"
              onClick={() => setIsTenantMenuOpen((prev) => !prev)}
              className="px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white shadow-2xs flex items-center gap-2 transition cursor-pointer border border-slate-800"
            >
              <Building2 className="w-3.5 h-3.5 text-amber-400" />
              <span className="max-w-[130px] truncate">{currentTenant.name}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {isTenantMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-slate-200 p-2 z-50 animate-in fade-in zoom-in-95 duration-100">
                <span className="text-[10px] uppercase font-bold text-slate-400 px-3 py-1 block">
                  Select Operating Tenant / Company
                </span>
                <div className="space-y-1">
                  {AVAILABLE_TENANTS.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        if (onSelectTenant) onSelectTenant(t.id);
                        setIsTenantMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold flex items-center justify-between transition cursor-pointer ${
                        tenantId === t.id
                          ? "bg-slate-100 text-slate-900 font-bold"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      }`}
                    >
                      <div>
                        <div className="text-slate-900 font-bold">{t.name}</div>
                        <div className="text-[10px] text-slate-500">{t.tag}</div>
                      </div>
                      {tenantId === t.id && <Check className="w-4 h-4 text-emerald-600" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Language Switcher Container */}
          <div className="flex items-center p-0.5 bg-slate-100 border border-slate-200 rounded-xl text-xs font-bold shadow-2xs relative">
            <button
              type="button"
              onClick={() => {
                setLanguage("en");
                setIsLangMenuOpen(false);
              }}
              className={`px-2.5 py-1 rounded-lg transition cursor-pointer flex items-center gap-1 ${
                language === "en"
                  ? "bg-white text-slate-900 shadow-2xs font-black"
                  : "text-slate-500 hover:text-slate-900"
              }`}
              title="Switch to English"
            >
              <Globe className="w-3.5 h-3.5 text-blue-600" />
              <span>EN</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setLanguage("hi");
                setIsLangMenuOpen(false);
              }}
              className={`px-2.5 py-1 rounded-lg transition cursor-pointer flex items-center gap-1 ${
                language === "hi"
                  ? "bg-white text-purple-900 shadow-2xs font-black"
                  : "text-slate-500 hover:text-slate-900"
              }`}
              title="?????? ??? ?????"
            >
              <span>??????</span>
            </button>

            {/* 3-dot Dropdown */}
            <div className="relative" ref={langDropdownRef}>
              <button
                type="button"
                onClick={() => setIsLangMenuOpen((prev) => !prev)}
                className={`px-2 py-1 rounded-lg transition cursor-pointer flex items-center justify-center gap-1 ${
                  isDropdownActive
                    ? "bg-slate-900 text-white shadow-2xs font-black"
                    : isLangMenuOpen
                    ? "bg-slate-200 text-slate-900"
                    : "text-slate-500 hover:text-slate-900 hover:bg-slate-200/60"
                }`}
              >
                <MoreHorizontal className="w-4 h-4" />
                {isDropdownActive && (
                  <span className="text-[9px] uppercase font-mono px-1 bg-blue-500 text-white rounded">
                    {language}
                  </span>
                )}
              </button>

              {isLangMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-2xl shadow-xl border border-slate-200 p-1.5 z-50">
                  <div className="text-[10px] font-bold text-slate-400 px-3 py-1 uppercase tracking-wider">
                    Indian Languages (?????? ??????)
                  </div>
                  <div className="space-y-0.5">
                    {DROPDOWN_LANGUAGES.map((lang) => (
                      <button
                        key={lang.code}
                        type="button"
                        onClick={() => {
                          setLanguage(lang.code);
                          setIsLangMenuOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2 rounded-xl text-xs font-semibold flex items-center justify-between transition cursor-pointer ${
                          language === lang.code
                            ? "bg-slate-100 text-slate-900 font-bold"
                            : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                        }`}
                      >
                        <div>
                          <span className="block font-medium">{lang.nativeScript}</span>
                          <span className="text-[10px] text-slate-400">{lang.englishName}</span>
                        </div>
                        {language === lang.code && <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </header>
  );
};
