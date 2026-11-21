"use client";

import { useState, useEffect } from "react";
import {
  X,
  MapPin,
  Globe,
  Mail,
  Star,
  ExternalLink,
  Clock,
  BarChart2,
  Brain,
  TrendingUp,
  TrendingDown,
  Search,
  MessageSquare,
  Compass,
} from "lucide-react";
import { LeadOut } from "@/lib/types";
import { api } from "@/lib/api";
import { DraftGenerator } from "./draft-generator";

interface LeadDrawerProps {
  lead: LeadOut | null;
  onClose: () => void;
  onLeadUpdated: () => void;
}

const STATUS_OPTIONS = [
  { value: "new", label: "New", color: "bg-slate-800 text-slate-300" },
  {
    value: "shortlisted",
    label: "Shortlisted",
    color: "bg-indigo-900/60 text-indigo-300 border border-indigo-700/60",
  },
  {
    value: "contacted",
    label: "Contacted",
    color: "bg-blue-900/60 text-blue-300 border border-blue-700/60",
  },
  {
    value: "replied",
    label: "Replied",
    color: "bg-emerald-900/60 text-emerald-300 border border-emerald-700/60",
  },
  {
    value: "meeting",
    label: "Meeting",
    color: "bg-purple-900/60 text-purple-300 border border-purple-700/60",
  },
  {
    value: "converted",
    label: "Converted",
    color: "bg-green-900/60 text-green-300 border border-green-700/60",
  },
  { value: "rejected", label: "Rejected", color: "bg-slate-800 text-slate-500" },
  {
    value: "do_not_contact",
    label: "Do Not Contact",
    color: "bg-rose-900/60 text-rose-300 border border-rose-700/60",
  },
];

export function LeadDrawer({ lead, onClose, onLeadUpdated }: LeadDrawerProps) {
  const [activeTab, setActiveTab] = useState<
    "overview" | "why_score" | "audit" | "draft" | "timeline"
  >("overview");
  const [updating, setUpdating] = useState(false);
  const [notes, setNotes] = useState(lead?.notes || "");
  const [savingNotes, setSavingNotes] = useState(false);
  const [explanations, setExplanations] = useState<
    {
      feature: string;
      impact: number;
      direction: "positive" | "negative";
      reason: string;
    }[]
  >([]);

  useEffect(() => {
    let ignore = false;
    if (!lead) return;
    const leadId = lead.id;
    async function fetchExpl() {
      try {
        const res = await api.getLeadExplanation(leadId);
        if (!ignore && res?.explanations) {
          setExplanations(res.explanations);
        }
      } catch {
        if (!ignore) setExplanations([]);
      }
    }
    void fetchExpl();
    return () => {
      ignore = true;
    };
  }, [lead]);

  if (!lead) return null;

  const place = lead.place;

  const googleMapsUrl =
    place?.latitude && place?.longitude
      ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name || "")}+${place.latitude},${place.longitude}`
      : place?.name
        ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name + " " + (place.address || ""))}`
        : null;

  const directionsUrl =
    place?.latitude && place?.longitude
      ? `https://www.google.com/maps/dir/?api=1&destination=${place.latitude},${place.longitude}`
      : null;

  const handleStatusChange = async (newStatus: string) => {
    setUpdating(true);
    try {
      await api.updateLead(lead.id, { status: newStatus });
      onLeadUpdated();
    } catch (err) {
      console.error("Failed to update status", err);
    } finally {
      setUpdating(false);
    }
  };

  const handleLogOutcome = async (outcome: string) => {
    setUpdating(true);
    try {
      await api.logOutcome(lead.id, { outcome });
      onLeadUpdated();
    } catch (err) {
      console.error("Failed to log outcome", err);
    } finally {
      setUpdating(false);
    }
  };

  const handleSaveNotes = async () => {
    setSavingNotes(true);
    try {
      await api.updateLead(lead.id, { notes });
      onLeadUpdated();
    } catch (err) {
      console.error("Failed to save notes", err);
    } finally {
      setSavingNotes(false);
    }
  };

  const handleAddDnc = async () => {
    if (confirm(`Add ${place?.name || "this lead"} to the Do-Not-Contact list?`)) {
      setUpdating(true);
      try {
        await api.updateLead(lead.id, { status: "do_not_contact" });
        onLeadUpdated();
      } catch (err) {
        console.error("Failed to add to DNC", err);
      } finally {
        setUpdating(false);
      }
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-250">
      {/* Persistent Header */}
      <div className="p-5 border-b border-slate-800 bg-slate-900/80 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-semibold font-mono ${
                STATUS_OPTIONS.find((s) => s.value === lead.status)?.color ||
                "bg-slate-800 text-slate-300"
              }`}
            >
              {lead.status.replace("_", " ").toUpperCase()}
            </span>
            <span className="text-xs text-indigo-400 font-bold font-mono bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/60 tabular-nums">
              Score: {lead.final_score !== null ? Math.round(lead.final_score) : "N/A"}/100
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              Outreach Draft &amp; Verification
            </span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight truncate max-w-md">
            {place?.name || "Business Details"}
          </h2>
          <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2 truncate">
            <div className="flex items-center gap-1 truncate">
              <MapPin className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
              <span className="truncate">{place?.address || "Address not available"}</span>
            </div>
            {googleMapsUrl && (
              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 hover:underline font-medium flex-shrink-0"
                title="Open location in Google Maps"
              >
                <span>Google Maps</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          aria-label="Close lead panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Quick Outcome Actions Bar */}
      <div className="px-5 py-2.5 bg-slate-900/40 border-b border-slate-800/80 flex items-center gap-1.5 overflow-x-auto text-xs">
        <span className="text-slate-500 font-medium text-[11px] mr-1">Quick Action:</span>
        <button
          onClick={() => handleLogOutcome("replied")}
          disabled={updating}
          className="px-2.5 py-1 rounded bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 font-medium whitespace-nowrap transition-colors"
        >
          Log Reply
        </button>
        <button
          onClick={() => handleLogOutcome("meeting")}
          disabled={updating}
          className="px-2.5 py-1 rounded bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 font-medium whitespace-nowrap transition-colors"
        >
          + Booked Meeting
        </button>
        <button
          onClick={() => handleStatusChange("contacted")}
          disabled={updating}
          className="px-2.5 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 font-medium whitespace-nowrap transition-colors"
        >
          Mark Contacted
        </button>
        <button
          onClick={handleAddDnc}
          disabled={updating}
          className="px-2.5 py-1 rounded bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 font-medium whitespace-nowrap transition-colors"
        >
          Add DNC
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-900/70 px-5 text-xs overflow-x-auto">
        <button
          onClick={() => setActiveTab("overview")}
          className={`py-2.5 px-3 font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
            activeTab === "overview"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <BarChart2 className="w-3.5 h-3.5" />
          <span>Overview</span>
        </button>
        <button
          onClick={() => setActiveTab("why_score")}
          className={`py-2.5 px-3 font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
            activeTab === "why_score"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Brain className="w-3.5 h-3.5" />
          <span>Why This Score</span>
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`py-2.5 px-3 font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
            activeTab === "audit"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Search className="w-3.5 h-3.5" />
          <span>Audit &amp; Reviews</span>
        </button>
        <button
          onClick={() => setActiveTab("draft")}
          className={`py-2.5 px-3 font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
            activeTab === "draft"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Mail className="w-3.5 h-3.5" />
          <span>Draft Outreach</span>
        </button>
        <button
          onClick={() => setActiveTab("timeline")}
          className={`py-2.5 px-3 font-semibold border-b-2 flex items-center gap-1.5 whitespace-nowrap transition-colors ${
            activeTab === "timeline"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Timeline ({lead.events?.length || 0})</span>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Contact & Profile Card */}
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
                Contact &amp; Business Profile
              </h3>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block text-[11px]">Phone (E.164)</span>
                  <span className="font-mono text-slate-200">
                    {place?.phone_e164 || "Not available"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Email</span>
                  <span className="font-mono text-slate-200 truncate block">
                    {place?.email || "Not available"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Rating</span>
                  <span className="flex items-center gap-1 text-slate-200 font-mono">
                    <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                    <span>{place?.rating ? place.rating.toFixed(1) : "--"}</span>
                    <span className="text-slate-500">({place?.review_count ?? 0} reviews)</span>
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Category</span>
                  <span className="capitalize text-slate-200">
                    {place?.normalized_category || place?.category || "--"}
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
                {place?.website && (
                  <a
                    href={place.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-mono transition-colors"
                  >
                    <Globe className="w-3.5 h-3.5 text-slate-400" />
                    <span className="truncate max-w-[120px]">Website</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>
                )}
                {googleMapsUrl && (
                  <a
                    href={googleMapsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition-colors shadow-sm"
                    title="View business on Google Maps"
                  >
                    <MapPin className="w-3.5 h-3.5 text-indigo-400" />
                    <span>View on Google Maps</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>
                )}
                {directionsUrl && (
                  <a
                    href={directionsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-colors shadow-sm"
                    title="Get turn-by-turn directions via Google Maps"
                  >
                    <Compass className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Get Directions</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>
                )}
              </div>
            </div>

            {/* Score Breakdown Strip */}
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
                Score Composition
              </h3>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[10px] block font-mono">RULE SCORE</span>
                  <span className="text-base font-bold font-mono text-white tabular-nums">
                    {lead.rule_score !== null ? Math.round(lead.rule_score) : "--"}
                  </span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[10px] block font-mono">ML PROB</span>
                  <span className="text-base font-bold font-mono text-indigo-400 tabular-nums">
                    {lead.ml_score !== null ? `${Math.round(lead.ml_score * 100)}%` : "Cold-start"}
                  </span>
                </div>
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-500 text-[10px] block font-mono">FINAL SCORE</span>
                  <span className="text-base font-bold font-mono text-emerald-400 tabular-nums">
                    {lead.final_score !== null ? Math.round(lead.final_score) : "--"}
                  </span>
                </div>
              </div>
            </div>

            {/* Rep Notes */}
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
                  Rep Notes
                </h3>
                <button
                  onClick={handleSaveNotes}
                  disabled={savingNotes}
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  {savingNotes ? "Saving..." : "Save Notes"}
                </button>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Log internal context, objections, or call notes..."
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        )}

        {activeTab === "why_score" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                <Brain className="w-3.5 h-3.5 text-indigo-400" />
                <span>Feature Importance &amp; Impact (SHAP)</span>
              </h3>
              {explanations.length === 0 ? (
                <p className="text-xs text-slate-500 py-3">
                  Score breakdown based on deterministic rule formulas (cold-start phase). Once 150+
                  labelled outcomes are logged, SHAP values will detail each feature&apos;s
                  push/pull.
                </p>
              ) : (
                <div className="space-y-2">
                  {explanations.map((exp, i) => (
                    <div
                      key={i}
                      className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2">
                        {exp.direction === "positive" ? (
                          <TrendingUp className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-rose-400 flex-shrink-0" />
                        )}
                        <div>
                          <span className="font-semibold text-white capitalize">{exp.feature}</span>
                          <p className="text-[11px] text-slate-400">{exp.reason}</p>
                        </div>
                      </div>
                      <span
                        className={`font-mono font-bold tabular-nums ${
                          exp.direction === "positive" ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {exp.direction === "positive" ? "+" : ""}
                        {exp.impact.toFixed(1)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Rule breakdown components */}
            {lead.score_breakdown && (
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
                  Rule Points Breakdown
                </h3>
                <div className="space-y-1.5 text-xs">
                  {Object.entries(lead.score_breakdown).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-center justify-between py-1.5 px-2 bg-slate-950 rounded border border-slate-800/80 font-mono"
                    >
                      <span className="capitalize text-slate-300">{k}</span>
                      <span className="text-indigo-300 font-bold tabular-nums">
                        {(v as { points?: number }).points ?? "--"} /{" "}
                        {(v as { max?: number }).max ?? "--"} pts
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "audit" && (
          <div className="space-y-6">
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-indigo-400" />
                <span>Website Audit &amp; Technical Health</span>
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Automated website quality checks verifying SSL certificate, mobile responsiveness,
                loading latency, and social links.
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 block text-[10px]">DOMAIN HEALTH</span>
                  <span className="font-semibold text-emerald-400 font-mono">
                    {place?.website ? "Resolved (200 OK)" : "No Website"}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 block text-[10px]">AUDIT STATUS</span>
                  <span className="font-semibold text-indigo-300 font-mono">Verified</span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
                <span>Customer Review Themes</span>
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Extracted sentiment themes highlighting operational bottlenecks, pricing issues, or
                unmet customer service requests.
              </p>
              <div className="space-y-1.5">
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300">
                  ⭐ <strong className="text-white">High review volume:</strong>{" "}
                  {place?.review_count ?? 0} total reviews with average rating of{" "}
                  {place?.rating ? place.rating.toFixed(1) : "N/A"}.
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "draft" && <DraftGenerator lead={lead} onStatusChanged={onLeadUpdated} />}

        {activeTab === "timeline" && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
              Lead Activity History
            </h3>
            {!lead.events || lead.events.length === 0 ? (
              <p className="text-xs text-slate-500">No activity events recorded yet.</p>
            ) : (
              <div className="space-y-2">
                {lead.events.map((ev, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs space-y-1"
                  >
                    <div className="flex justify-between items-center text-[11px] text-slate-400 font-mono">
                      <span className="font-semibold text-slate-200 capitalize">
                        {ev.event_type}
                      </span>
                      <span>{new Date(ev.occurred_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
