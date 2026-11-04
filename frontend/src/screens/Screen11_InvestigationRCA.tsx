import React, { useState, useEffect } from "react";
import { ReportItem } from "../types";
import {
  FileCheck2,
  Printer,
  Layers,
  Wrench,
  Users,
  Wind,
  ShieldAlert,
  CheckCircle2
} from "lucide-react";

interface Screen11Props {
  report: ReportItem;
  onOpenExportModal: () => void;
}

export const Screen11_InvestigationRCA: React.FC<Screen11Props> = ({
  report,
  onOpenExportModal
}) => {
  const [why1, setWhy1] = useState("");
  const [why2, setWhy2] = useState("");
  const [why3, setWhy3] = useState("");
  const [why4, setWhy4] = useState("");
  const [why5, setWhy5] = useState("");

  const [engAction, setEngAction] = useState("");
  const [adminAction, setAdminAction] = useState("");
  const [toolboxAction, setToolboxAction] = useState("");

  const barrierName = report?.extraction?.barriers?.[0]?.display_name || report?.extraction?.barriers?.[0]?.canonical_barrier || "Safety Barrier";
  const barrierState = report?.extraction?.barriers?.[0]?.barrier_status || "UNVERIFIED";
  const hazardName = report?.extraction?.hazards?.[0]?.display_name || report?.extraction?.hazards?.[0]?.canonical_hazard || "hazardous energy";
  const energyType = report?.extraction?.energy_type || "operational energy";
  const consequence = report?.extraction?.potential_consequence || "potential serious injury or fatality";
  const lsrName = report?.rule_mappings?.[0]?.rule_display_name || "IOGP Life-Saving Rule";
  const exposureDesc = report?.extraction?.exposure?.description;

  useEffect(() => {
    if (!report) return;

    setWhy1(`Direct physical hazard: ${hazardName} was active with potential for ${consequence}.`);
    setWhy2(`Primary safety barrier '${barrierName}' was in an '${barrierState}' state, failing to contain ${energyType} energy.`);
    setWhy3(`Pre-task positive verification test or physical barrier integrity validation for ${energyType} was incomplete: ${exposureDesc || "personnel were within proximity without positive isolation confirmation"}.`);
    setWhy4(`Work authorization or task-level verification checklist for ${(report.activity || "site work").replace(/_/g, " ")} missed mandatory hold-point before operations.`);
    setWhy5(`Systemic procedural drift, latent degradation in ${lsrName} safeguard verification, and absence of secondary barrier cross-verification.`);

    setEngAction(`Mandate engineered positive isolation lockout and calibrated sensor verification for ${barrierName}.`);
    setAdminAction(`Revise PTW checklist to include mandatory dual-signoff hold-point for all ${lsrName} critical tasks.`);
    setToolboxAction(`Conduct immediate stand-down & toolbox talk across ${report.site || "all facilities"} on ${lsrName} precursor recognition.`);
  }, [report?.report_id]);

  // Derived Ishikawa Fishbone Items based on real report extraction
  const ishikawaPeople = [
    report.contractor_involved ? "Contractor competency & orientation verification gap" : "Internal crew shift turnover & workload pacing",
    `Familiarity drift regarding ${lsrName} non-negotiables`,
    "Assumed barrier status without independent verification"
  ];

  const ishikawaEquipment = [
    `${barrierName} physical condition: marked as ${barrierState}`,
    `${energyType.toUpperCase()} containment hardware & isolation points`,
    "Lockout/tagout device fitment and testing apparatus"
  ];

  const ishikawaProcess = [
    `PTW certificate and ${lsrName} requirement alignment`,
    "Pre-task safety meeting (TBT) hazard identification depth",
    "Line-of-fire barricade and exclusion zone enforcement"
  ];

  const ishikawaEnvironment = [
    `Facility operational footprint at ${report.site || "field location"}`,
    "Ambient noise, lighting, and weather exposure during task execution",
    "Simultaneous operations (SIMOPS) congestion and distraction"
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="bg-gradient-to-r from-white via-purple-50/50 to-indigo-50/50 rounded-3xl p-7 border border-slate-200/90 flex flex-wrap items-center justify-between gap-6 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-2xl bg-purple-100 text-purple-700">
            <FileCheck2 className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold text-slate-900 m-0 tracking-tight">
              Investigation Studio & Root Cause Analysis (RCA) Assistant
            </h2>
            <p className="text-sm text-slate-500 m-0 font-medium">
              Accelerating human investigations with pre-populated 5-Whys, Ishikawa Fishbone diagrams, and Hierarchy of Controls
            </p>
          </div>
        </div>

        <button
          onClick={onOpenExportModal}
          className="flex items-center gap-2.5 px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold text-xs shadow-xs transition active:scale-95 cursor-pointer"
        >
          <Printer className="w-4 h-4" />
          <span>Export Official PDF Investigation Pack</span>
        </button>
      </div>

      {/* Target Report Context */}
      <div className="p-6 rounded-3xl bg-white border border-slate-200/90 flex flex-wrap items-center justify-between gap-6 shadow-xs">
        <div className="space-y-1.5 max-w-3xl">
          <span className="text-xs text-slate-500 uppercase tracking-wider block font-bold">Target Observation Under Investigation:</span>
          <h4 className="text-sm font-extrabold text-slate-900 m-0">{report.title || report.site} (Ref: {report.external_ref})</h4>
          <p className="text-sm text-slate-800 italic mt-1 m-0 font-medium leading-relaxed">"{report.narrative_text}"</p>
        </div>
        <div className="text-right shrink-0 space-y-1">
          <span className="text-sm font-extrabold text-rose-700 font-mono block">{report.assessment?.sif_potential_label} SIF POTENTIAL</span>
          <span className="text-xs text-indigo-800 font-bold bg-indigo-50 px-2.5 py-1 rounded border border-indigo-200 block">IOGP: {report.rule_mappings?.[0]?.rule_display_name || "PSF"}</span>
        </div>
      </div>

      {/* 5-Whys Interactive Studio */}
      <div className="bg-white rounded-3xl p-7 border border-slate-200/90 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3.5">
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-1 rounded-lg bg-indigo-100 text-indigo-800 font-mono font-extrabold text-xs">
              5-Whys
            </span>
            <h3 className="text-base font-bold text-slate-900 m-0">
              Interactive 5-Whys Causal Drill-Down
            </h3>
          </div>
          <span className="text-xs text-slate-500 italic font-medium">Editable starting point for HSE lead investigator</span>
        </div>

        <div className="space-y-4 text-sm">
          <div className="space-y-1.5">
            <label className="text-slate-800 font-bold block text-xs uppercase tracking-wider">1. Why was there potential for serious injury?</label>
            <input
              type="text"
              value={why1}
              onChange={(e) => setWhy1(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-slate-900 text-sm font-medium focus:ring-2 focus:ring-indigo-500 focus:bg-white transition shadow-2xs"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-800 font-bold block text-xs uppercase tracking-wider">2. Why was energy uncontrolled?</label>
            <input
              type="text"
              value={why2}
              onChange={(e) => setWhy2(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-slate-900 text-sm font-medium focus:ring-2 focus:ring-indigo-500 focus:bg-white transition shadow-2xs"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-800 font-bold block text-xs uppercase tracking-wider">3. Why was the barrier in this failure state?</label>
            <input
              type="text"
              value={why3}
              onChange={(e) => setWhy3(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-slate-900 text-sm font-medium focus:ring-2 focus:ring-indigo-500 focus:bg-white transition shadow-2xs"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-800 font-bold block text-xs uppercase tracking-wider">4. Why was verification skipped or not documented?</label>
            <input
              type="text"
              value={why4}
              onChange={(e) => setWhy4(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-slate-900 text-sm font-medium focus:ring-2 focus:ring-indigo-500 focus:bg-white transition shadow-2xs"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-purple-950 font-bold block text-xs uppercase tracking-wider">5. Root Latent Organizational Cause:</label>
            <input
              type="text"
              value={why5}
              onChange={(e) => setWhy5(e.target.value)}
              className="w-full bg-purple-50/80 border border-purple-300 rounded-xl px-4 py-2.5 text-purple-950 font-extrabold text-sm focus:ring-2 focus:ring-purple-500 focus:bg-white transition shadow-2xs"
            />
          </div>
        </div>
      </div>

      {/* Ishikawa Fishbone Diagram Cards */}
      <div className="bg-white rounded-3xl p-7 border border-slate-200/90 shadow-sm space-y-5">
        <h3 className="text-base font-bold text-slate-900 tracking-wide m-0">
          Ishikawa Fishbone Dimension Analysis
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-sm">
          {/* People */}
          <div className="p-5 rounded-2xl bg-indigo-50/70 border border-indigo-200 space-y-2.5">
            <div className="flex items-center gap-2.5 text-indigo-900 font-extrabold">
              <Users className="w-5 h-5" />
              <span>People & Competency</span>
            </div>
            <ul className="space-y-2 text-slate-700 pl-4 list-disc m-0 text-xs font-medium">
              {ishikawaPeople.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>

          {/* Equipment */}
          <div className="p-5 rounded-2xl bg-amber-50/70 border border-amber-200 space-y-2.5">
            <div className="flex items-center gap-2.5 text-amber-900 font-extrabold">
              <Wrench className="w-5 h-5" />
              <span>Equipment & Hardware</span>
            </div>
            <ul className="space-y-2 text-slate-700 pl-4 list-disc m-0 text-xs font-medium">
              {ishikawaEquipment.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>

          {/* Process */}
          <div className="p-5 rounded-2xl bg-purple-50/70 border border-purple-200 space-y-2.5">
            <div className="flex items-center gap-2.5 text-purple-900 font-extrabold">
              <Layers className="w-5 h-5" />
              <span>Process & Procedures</span>
            </div>
            <ul className="space-y-2 text-slate-700 pl-4 list-disc m-0 text-xs font-medium">
              {ishikawaProcess.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>

          {/* Environment */}
          <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2.5">
            <div className="flex items-center gap-2.5 text-emerald-900 font-extrabold">
              <Wind className="w-5 h-5" />
              <span>Work Environment</span>
            </div>
            <ul className="space-y-2 text-slate-700 pl-4 list-disc m-0 text-xs font-medium">
              {ishikawaEnvironment.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Recommended Actions: Hierarchy of Controls */}
      <div className="bg-white rounded-3xl p-7 border border-slate-200/90 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3.5">
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-800 font-mono font-extrabold text-xs">
              Actions
            </span>
            <h3 className="text-base font-bold text-slate-900 m-0">
              AI-Drafted Recommended Actions (Hierarchy of Controls)
            </h3>
          </div>
          <span className="text-xs text-slate-500 italic font-medium">Human-editable HSE action plan</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
          {/* Engineering Control */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2.5">
            <div className="flex items-center gap-2 text-indigo-900 font-extrabold text-xs uppercase tracking-wider">
              <ShieldAlert className="w-4 h-4 text-indigo-600" />
              <span>Engineering Control</span>
            </div>
            <textarea
              rows={3}
              value={engAction}
              onChange={(e) => setEngAction(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-xl p-3 text-slate-800 text-xs font-medium focus:ring-2 focus:ring-indigo-500 transition shadow-2xs resize-none"
            />
          </div>

          {/* Administrative Control */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2.5">
            <div className="flex items-center gap-2 text-amber-900 font-extrabold text-xs uppercase tracking-wider">
              <Layers className="w-4 h-4 text-amber-600" />
              <span>Administrative Control</span>
            </div>
            <textarea
              rows={3}
              value={adminAction}
              onChange={(e) => setAdminAction(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-xl p-3 text-slate-800 text-xs font-medium focus:ring-2 focus:ring-amber-500 transition shadow-2xs resize-none"
            />
          </div>

          {/* Toolbox Talk / Awareness */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2.5">
            <div className="flex items-center gap-2 text-emerald-900 font-extrabold text-xs uppercase tracking-wider">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Toolbox Talk Topic</span>
            </div>
            <textarea
              rows={3}
              value={toolboxAction}
              onChange={(e) => setToolboxAction(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-xl p-3 text-slate-800 text-xs font-medium focus:ring-2 focus:ring-emerald-500 transition shadow-2xs resize-none"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
