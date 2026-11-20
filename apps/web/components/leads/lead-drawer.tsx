"use client";

import { useState } from "react";
import {
  X,
  MapPin,
  Globe,
  Phone,
  Mail,
  Star,
  ExternalLink,
  ShieldAlert,
  Clock,
  BarChart2,
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
  { value: "new", label: "New", color: "bg-gray-800 text-gray-300" },
  { value: "shortlisted", label: "Shortlisted", color: "bg-indigo-900/60 text-indigo-300" },
  { value: "contacted", label: "Contacted", color: "bg-blue-900/60 text-blue-300" },
  { value: "replied", label: "Replied", color: "bg-emerald-900/60 text-emerald-300" },
  { value: "meeting", label: "Meeting", color: "bg-purple-900/60 text-purple-300" },
  { value: "converted", label: "Converted", color: "bg-green-900/60 text-green-300" },
  { value: "rejected", label: "Rejected", color: "bg-gray-800 text-gray-500" },
  { value: "do_not_contact", label: "Do Not Contact", color: "bg-red-900/60 text-red-300" },
];

export function LeadDrawer({ lead, onClose, onLeadUpdated }: LeadDrawerProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "draft" | "timeline">("overview");
  const [updating, setUpdating] = useState(false);
  const [notes, setNotes] = useState(lead?.notes || "");
  const [savingNotes, setSavingNotes] = useState(false);

  if (!lead) return null;

  const place = lead.place;

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
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-gray-950 border-l border-gray-800 shadow-2xl flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-800 bg-gray-900/70 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                STATUS_OPTIONS.find((s) => s.value === lead.status)?.color ||
                "bg-gray-800 text-gray-300"
              }`}
            >
              {lead.status.replace("_", " ").toUpperCase()}
            </span>
            <span className="text-xs text-indigo-400 font-semibold bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/60">
              Score: {lead.final_score !== null ? Math.round(lead.final_score) : "N/A"}/100
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            {place?.name || "Business Details"}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5" />
            <span>{place?.address || "Address not available"}</span>
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 bg-gray-900 px-6">
        <button
          onClick={() => setActiveTab("overview")}
          className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition-colors ${
            activeTab === "overview"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <BarChart2 className="w-3.5 h-3.5" />
          <span>Overview & Score</span>
        </button>
        <button
          onClick={() => setActiveTab("draft")}
          className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition-colors ${
            activeTab === "draft"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Mail className="w-3.5 h-3.5" />
          <span>Outreach Draft</span>
        </button>
        <button
          onClick={() => setActiveTab("timeline")}
          className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition-colors ${
            activeTab === "timeline"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Timeline ({lead.events?.length || 0})</span>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Status Pipeline bar */}
        <div>
          <label className="text-xs font-medium text-gray-400 block mb-2">Lead Status</label>
          <div className="flex flex-wrap gap-1.5">
            {STATUS_OPTIONS.map((st) => (
              <button
                key={st.value}
                disabled={updating}
                onClick={() => handleStatusChange(st.value)}
                className={`text-xs px-2.5 py-1 rounded-md transition-all ${
                  lead.status === st.value
                    ? "ring-2 ring-indigo-400 font-bold " + st.color
                    : "opacity-60 hover:opacity-100 " + st.color
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>

        {/* Quick Log Outcome */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-3 space-y-2">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wider block">
            Log Outreach Outcome
          </label>
          <div className="grid grid-cols-4 gap-1.5 text-xs">
            <button
              onClick={() => handleLogOutcome("replied")}
              disabled={updating}
              className="py-1.5 px-2 bg-emerald-950/70 hover:bg-emerald-900/90 text-emerald-300 border border-emerald-800/80 rounded-md font-medium text-center transition-colors"
            >
              Replied
            </button>
            <button
              onClick={() => handleLogOutcome("meeting")}
              disabled={updating}
              className="py-1.5 px-2 bg-purple-950/70 hover:bg-purple-900/90 text-purple-300 border border-purple-800/80 rounded-md font-medium text-center transition-colors"
            >
              Meeting
            </button>
            <button
              onClick={() => handleLogOutcome("converted")}
              disabled={updating}
              className="py-1.5 px-2 bg-green-950/70 hover:bg-green-900/90 text-green-300 border border-green-800/80 rounded-md font-medium text-center transition-colors"
            >
              Converted
            </button>
            <button
              onClick={() => handleLogOutcome("no_reply")}
              disabled={updating}
              className="py-1.5 px-2 bg-gray-950 hover:bg-gray-800 text-gray-400 border border-gray-800 rounded-md font-medium text-center transition-colors"
            >
              No Reply
            </button>
          </div>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Business Contact Facts */}
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-2 text-xs">
              <h4 className="font-semibold text-gray-300 text-xs uppercase tracking-wider mb-2">
                Business Information
              </h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center gap-2 text-gray-300">
                  <Star className="w-3.5 h-3.5 text-amber-400" />
                  <span>
                    Rating:{" "}
                    <strong className="text-white">
                      {place?.rating ? place.rating.toFixed(1) : "N/A"}
                    </strong>{" "}
                    ({place?.review_count ?? 0} reviews)
                  </span>
                </div>
                <div className="flex items-center gap-2 text-gray-300">
                  <Phone className="w-3.5 h-3.5 text-indigo-400" />
                  <span>{place?.phone_e164 || "No phone listed"}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-300 col-span-2">
                  <Mail className="w-3.5 h-3.5 text-indigo-400" />
                  <span>{place?.email || "No email detected"}</span>
                </div>
                {place?.website && (
                  <div className="flex items-center gap-2 text-gray-300 col-span-2 truncate">
                    <Globe className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                    <a
                      href={place.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 hover:underline flex items-center gap-1 truncate"
                    >
                      <span className="truncate">{place.website}</span>
                      <ExternalLink className="w-3 h-3 shrink-0" />
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Score Breakdown Popover/Section */}
            <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 space-y-3">
              <h4 className="font-semibold text-gray-300 text-xs uppercase tracking-wider">
                Score Breakdown (0 - 100)
              </h4>
              <div className="space-y-2 text-xs">
                {Object.entries(lead.score_breakdown || {}).map(([key, item]) => {
                  if (typeof item !== "object" || item === null) return null;
                  const comp = item as { points?: number; max?: number; reason?: string };
                  return (
                    <div
                      key={key}
                      className="p-2.5 rounded-lg bg-gray-950/70 border border-gray-800/80"
                    >
                      <div className="flex items-center justify-between font-medium text-gray-200">
                        <span className="capitalize">{key}</span>
                        <span className="text-indigo-400 font-mono">
                          +{comp.points ?? 0} / {comp.max ?? "-"} pts
                        </span>
                      </div>
                      {comp.reason && <p className="text-gray-400 text-xs mt-1">{comp.reason}</p>}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Internal Notes */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">
                Internal Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add private context, meeting outcomes, or lead objections..."
                rows={3}
                className="w-full bg-gray-900 border border-gray-800 rounded-lg p-3 text-xs text-white placeholder-gray-500 focus:ring-1 focus:ring-indigo-500"
              />
              <button
                onClick={handleSaveNotes}
                disabled={savingNotes}
                className="py-1 px-3 bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium rounded-md transition-colors"
              >
                {savingNotes ? "Saving..." : "Save Notes"}
              </button>
            </div>

            {/* DNC Exclusion Action */}
            {lead.status !== "do_not_contact" && (
              <div className="pt-4 border-t border-gray-800">
                <button
                  onClick={handleAddDnc}
                  className="w-full py-2 bg-red-950/40 hover:bg-red-900/60 border border-red-800 text-red-300 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <ShieldAlert className="w-4 h-4 text-red-400" />
                  <span>Add to Do-Not-Contact List</span>
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === "draft" && (
          <div className="space-y-4">
            <DraftGenerator
              lead={lead}
              onDraftGenerated={() => onLeadUpdated()}
              onStatusChanged={() => onLeadUpdated()}
            />
          </div>
        )}

        {activeTab === "timeline" && (
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-300 text-xs uppercase tracking-wider mb-3">
              Event History
            </h4>
            {!lead.events || lead.events.length === 0 ? (
              <p className="text-gray-500 text-xs">No outreach events logged yet.</p>
            ) : (
              <div className="space-y-2">
                {lead.events.map((ev) => (
                  <div
                    key={ev.id}
                    className="p-3 rounded-lg bg-gray-900 border border-gray-800 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-indigo-300 capitalize">
                        {ev.event_type}
                      </span>
                      <span className="text-gray-500 text-[10px]">
                        {new Date(ev.occurred_at).toLocaleString()}
                      </span>
                    </div>
                    {ev.features_snapshot && Object.keys(ev.features_snapshot).length > 0 && (
                      <div className="text-[11px] text-gray-400 bg-gray-950 p-2 rounded border border-gray-800/60">
                        <span className="text-gray-500 font-mono">Frozen Snapshot: </span>
                        <span>
                          {Object.keys(ev.features_snapshot).length} features captured at contact
                          time
                        </span>
                      </div>
                    )}
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
