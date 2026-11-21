"use client";

import { useState } from "react";
import {
  Copy,
  Check,
  Mail,
  MessageSquare,
  Send,
  AlertTriangle,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { GeneratedDraftOut, LeadOut } from "@/lib/types";
import { api } from "@/lib/api";

interface DraftGeneratorProps {
  lead: LeadOut;
  onDraftGenerated?: (draft: GeneratedDraftOut) => void;
  onStatusChanged?: () => void;
}

export function DraftGenerator({ lead, onDraftGenerated, onStatusChanged }: DraftGeneratorProps) {
  const [channel, setChannel] = useState<"email" | "chat">("email");
  const [tone, setTone] = useState<string>("direct");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<GeneratedDraftOut | null>(null);
  const [copied, setCopied] = useState(false);
  const [markingContacted, setMarkingContacted] = useState(false);

  const isDNC = lead.status === "do_not_contact";

  const handleGenerate = async () => {
    if (isDNC) {
      setError("This lead is on the Do-Not-Contact list. Outreach drafts are strictly prohibited.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await api.generateDraft(lead.id, {
        channel,
        tone,
      });
      setDraft(result);
      if (onDraftGenerated) {
        onDraftGenerated(result);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate draft";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!draft?.body) return;
    navigator.clipboard.writeText(draft.body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleMarkContacted = async () => {
    setMarkingContacted(true);
    try {
      await api.updateLead(lead.id, { status: "contacted" });
      if (onStatusChanged) {
        onStatusChanged();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update lead status";
      setError(msg);
    } finally {
      setMarkingContacted(false);
    }
  };

  if (isDNC) {
    return (
      <div className="rounded-xl bg-rose-950/40 border border-rose-800 p-4 text-rose-300 text-xs flex items-center gap-2.5">
        <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
        <span>This business is on the Do-Not-Contact list. Outreach drafts cannot be created.</span>
      </div>
    );
  }

  // Count chars and words
  const charCount = draft?.body ? draft.body.length : 0;
  const wordCount = draft?.body ? draft.body.trim().split(/\s+/).filter(Boolean).length : 0;
  const maxChars = 450;
  const maxWords = 120;

  // Build mailto and wa.me links
  const place = lead.place;
  const mailtoUrl = place?.email
    ? `mailto:${encodeURIComponent(place.email)}?subject=${encodeURIComponent(
        `GapScout intelligence for ${place.name}`,
      )}&body=${encodeURIComponent(draft?.body || "")}`
    : null;

  const phoneRaw = place?.phone_e164?.replace(/\D/g, "");
  const waUrl = phoneRaw
    ? `https://wa.me/${phoneRaw}?text=${encodeURIComponent(draft?.body || "")}`
    : `https://wa.me/?text=${encodeURIComponent(draft?.body || "")}`;

  return (
    <div className="space-y-4 rounded-xl bg-slate-900/60 border border-slate-800 p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-white text-xs flex items-center gap-2">
          <Send className="w-3.5 h-3.5 text-indigo-400" />
          <span>Outreach Draft Generator (Draft Only)</span>
        </h4>
        <div className="text-[10px] text-amber-400 font-mono bg-amber-950/50 px-2 py-0.5 rounded border border-amber-800">
          Human-in-the-loop
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <label className="text-slate-400 block mb-1 font-medium text-[11px]">Channel</label>
          <div className="grid grid-cols-2 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button
              type="button"
              onClick={() => setChannel("email")}
              className={`py-1 px-2 rounded flex items-center justify-center gap-1.5 transition-colors text-xs ${
                channel === "email"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Mail className="w-3 h-3" />
              <span>Email</span>
            </button>
            <button
              type="button"
              onClick={() => setChannel("chat")}
              className={`py-1 px-2 rounded flex items-center justify-center gap-1.5 transition-colors text-xs ${
                channel === "chat"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <MessageSquare className="w-3 h-3" />
              <span>WhatsApp</span>
            </button>
          </div>
        </div>

        <div>
          <label className="text-slate-400 block mb-1 font-medium text-[11px]">Tone</label>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg py-1.5 px-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="direct">Direct &amp; High-Value</option>
            <option value="consultative">Consultative &amp; Soft</option>
            <option value="metric_focused">Evidence-Backed</option>
          </select>
        </div>
      </div>

      <button
        type="button"
        onClick={handleGenerate}
        disabled={loading}
        className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors shadow-sm"
      >
        {loading ? (
          <>
            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>Drafting with Grounded Metrics...</span>
          </>
        ) : (
          <>
            <Send className="w-3.5 h-3.5" />
            <span>Generate Grounded Draft</span>
          </>
        )}
      </button>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Render Draft Preview */}
      {draft && (
        <div className="space-y-3 pt-3 border-t border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>PREVIEW</span>
            <div className="flex items-center gap-2">
              <span className="tabular-nums">
                {channel === "email"
                  ? `${wordCount}/${maxWords} words`
                  : `${charCount}/${maxChars} chars`}
              </span>
              <span className="text-emerald-400 font-bold">Grounded [N]</span>
            </div>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-2 text-xs">
            <div className="whitespace-pre-wrap text-slate-300 leading-relaxed font-sans text-xs">
              {draft.body}
            </div>

            {/* Highlighted Opt-Out Guarantee */}
            <div className="mt-3 pt-2.5 border-t border-slate-800/80 text-[11px] text-amber-300/90 bg-amber-950/30 p-2 rounded-lg flex items-center gap-1.5 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span>Mandatory opt-out statement included.</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button
              type="button"
              onClick={handleCopy}
              className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              <span>{copied ? "Copied!" : "Copy Text"}</span>
            </button>

            {mailtoUrl && (
              <a
                href={mailtoUrl}
                target="_blank"
                rel="noreferrer"
                className="py-1.5 px-3 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Mail className="w-3.5 h-3.5" />
                <span>Open Mail</span>
                <ExternalLink className="w-2.5 h-2.5" />
              </a>
            )}

            <a
              href={waUrl}
              target="_blank"
              rel="noreferrer"
              className="py-1.5 px-3 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Open WhatsApp</span>
              <ExternalLink className="w-2.5 h-2.5" />
            </a>

            <button
              type="button"
              onClick={handleMarkContacted}
              disabled={markingContacted || lead.status === "contacted"}
              className="py-1.5 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {markingContacted ? "Updating..." : "Mark Contacted"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
