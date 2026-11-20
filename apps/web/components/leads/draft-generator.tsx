"use client";

import { useState } from "react";
import { Copy, Check, Mail, MessageSquare, Send, AlertTriangle } from "lucide-react";
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
      <div className="rounded-lg bg-red-950/40 border border-red-800 p-4 text-red-300 text-sm flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
        <span>This business is on the Do-Not-Contact list. Outreach drafts cannot be created.</span>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-xl bg-gray-900 border border-gray-800 p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-white text-sm flex items-center gap-2">
          <Send className="w-4 h-4 text-indigo-400" />
          <span>Outreach Draft Generator (Draft Only)</span>
        </h4>
        <div className="text-xs text-amber-400 font-mono bg-amber-950/50 px-2 py-0.5 rounded border border-amber-800">
          Human-in-the-loop
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <label className="text-gray-400 block mb-1 font-medium">Channel</label>
          <div className="grid grid-cols-2 gap-1 bg-gray-950 p-1 rounded-lg border border-gray-800">
            <button
              type="button"
              onClick={() => setChannel("email")}
              className={`py-1.5 px-2 rounded flex items-center justify-center gap-1.5 transition-colors ${
                channel === "email"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Mail className="w-3.5 h-3.5" />
              <span>Email</span>
            </button>
            <button
              type="button"
              onClick={() => setChannel("chat")}
              className={`py-1.5 px-2 rounded flex items-center justify-center gap-1.5 transition-colors ${
                channel === "chat"
                  ? "bg-emerald-600 text-white font-semibold"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>WhatsApp</span>
            </button>
          </div>
        </div>

        <div>
          <label className="text-gray-400 block mb-1 font-medium">Tone</label>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg py-1.5 px-2.5 text-white text-xs focus:ring-1 focus:ring-indigo-500"
          >
            <option value="direct">Direct & Problem-Focused</option>
            <option value="consultative">Consultative & Helpful</option>
            <option value="casual">Casual & Conversational</option>
          </select>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            <span>Generating Grounded Draft...</span>
          </>
        ) : (
          <span>Generate Grounded Draft</span>
        )}
      </button>

      {error && (
        <div className="p-2.5 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-xs">
          {error}
        </div>
      )}

      {draft && (
        <div className="space-y-3 pt-2 border-t border-gray-800">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <div className="flex items-center gap-3">
              <span>
                Length: <strong className="text-white">{draft.word_count} words</strong>
              </span>
              <span>
                Chars: <strong className="text-white">{draft.char_count}</strong>
              </span>
            </div>
            <span className="text-emerald-400">Mandatory opt-out included</span>
          </div>

          <textarea
            value={draft.body}
            onChange={(e) => {
              const updatedBody = e.target.value;
              setDraft({
                ...draft,
                body: updatedBody,
                word_count: updatedBody.trim().split(/\s+/).length,
                char_count: updatedBody.length,
              });
            }}
            rows={7}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-xs text-gray-200 font-mono focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
          />

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex-1 py-1.5 px-3 bg-gray-800 hover:bg-gray-700 text-white text-xs font-medium rounded-lg flex items-center justify-center gap-1.5 transition-colors"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              <span>{copied ? "Copied!" : "Copy Text"}</span>
            </button>

            {draft.mailto_link && (
              <a
                href={draft.mailto_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-1.5 px-3 bg-indigo-900/60 hover:bg-indigo-800/80 text-indigo-200 border border-indigo-700/50 text-xs font-medium rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                <Mail className="w-3.5 h-3.5" />
                <span>Open in Mail</span>
              </a>
            )}

            {draft.wa_link && (
              <a
                href={draft.wa_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-1.5 px-3 bg-emerald-900/60 hover:bg-emerald-800/80 text-emerald-200 border border-emerald-700/50 text-xs font-medium rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Open WhatsApp</span>
              </a>
            )}
          </div>

          {lead.status !== "contacted" &&
            lead.status !== "replied" &&
            lead.status !== "meeting" &&
            lead.status !== "converted" && (
              <button
                onClick={handleMarkContacted}
                disabled={markingContacted}
                className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {markingContacted ? "Updating..." : "Mark as Contacted (Freeze Features)"}
              </button>
            )}
        </div>
      )}
    </div>
  );
}
