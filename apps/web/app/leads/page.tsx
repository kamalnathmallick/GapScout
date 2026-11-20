"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Users, ExternalLink, ChevronRight, Star, Mail, RefreshCw, Brain } from "lucide-react";
import { LeadOut } from "@/lib/types";
import { api } from "@/lib/api";
import { LeadDrawer } from "@/components/leads/lead-drawer";
import { DatasetHealthCard } from "@/components/dataset-health-card";

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [minScore, setMinScore] = useState<number>(0);
  const [hasEmail, setHasEmail] = useState<boolean>(false);
  const [includeDnc, setIncludeDnc] = useState<boolean>(false);
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listLeads({
        status: statusFilter || undefined,
        min_score: minScore > 0 ? minScore : undefined,
        has_email: hasEmail ? true : undefined,
        include_dnc: includeDnc,
        limit: 100,
      });
      setLeads(res.items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load leads";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, minScore, hasEmail, includeDnc]);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const res = await api.listLeads({
          status: statusFilter || undefined,
          min_score: minScore > 0 ? minScore : undefined,
          has_email: hasEmail ? true : undefined,
          include_dnc: includeDnc,
          limit: 100,
        });
        if (!ignore) {
          setLeads(res.items);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load leads";
          setError(msg);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      ignore = true;
    };
  }, [statusFilter, minScore, hasEmail, includeDnc]);

  const activeLead = leads.find((l) => l.id === selectedLeadId) || null;

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedLeadIds(leads.map((l) => l.id));
    } else {
      setSelectedLeadIds([]);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedLeadIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  };

  const handleBulkStatus = async (status: string) => {
    if (selectedLeadIds.length === 0) return;
    setBulkActionLoading(true);
    try {
      await Promise.all(selectedLeadIds.map((id) => api.updateLead(id, { status })));
      setSelectedLeadIds([]);
      fetchLeads();
    } catch (err) {
      console.error("Bulk status update failed", err);
    } finally {
      setBulkActionLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <Users className="w-6 h-6 text-indigo-400" />
              <span>Lead Scorer & Outreach Pipeline</span>
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Grounded, draft-only outreach workflow with zero automated sending and strict DNC
              protection.
            </p>
          </div>
          <div className="flex items-center gap-2 self-start md:self-auto">
            <Link
              href="/leads/active-learning"
              className="px-3.5 py-2 bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-800/80 rounded-lg text-xs font-semibold text-indigo-300 flex items-center gap-2 transition-colors"
            >
              <Brain className="w-3.5 h-3.5 text-indigo-400" />
              <span>Active-Learning Queue</span>
            </Link>
            <button
              onClick={() => fetchLeads()}
              disabled={loading}
              className="px-3.5 py-2 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg text-xs font-medium text-gray-300 flex items-center gap-2 transition-colors"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${loading ? "animate-spin text-indigo-400" : ""}`}
              />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Dataset Health & ML Unlock Status Card */}
        <div className="mb-6">
          <DatasetHealthCard />
        </div>

        {/* Filter Toolbar */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-4 mb-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              {/* Status Filter */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 font-medium">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-gray-950 border border-gray-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">All Active</option>
                  <option value="new">New</option>
                  <option value="shortlisted">Shortlisted</option>
                  <option value="contacted">Contacted</option>
                  <option value="replied">Replied</option>
                  <option value="meeting">Meeting</option>
                  <option value="converted">Converted</option>
                  <option value="rejected">Rejected</option>
                  <option value="do_not_contact">Do Not Contact</option>
                </select>
              </div>

              {/* Min Score Filter */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 font-medium">Min Score:</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="5"
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-16 bg-gray-950 border border-gray-800 rounded-lg px-2 py-1.5 text-xs text-white focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Has Email Toggle */}
              <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasEmail}
                  onChange={(e) => setHasEmail(e.target.checked)}
                  className="rounded bg-gray-950 border-gray-800 text-indigo-600 focus:ring-indigo-500"
                />
                <span>Has Email</span>
              </label>

              {/* Include DNC Toggle */}
              <label className="flex items-center gap-2 text-xs text-red-300/80 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeDnc}
                  onChange={(e) => setIncludeDnc(e.target.checked)}
                  className="rounded bg-gray-950 border-gray-800 text-red-600 focus:ring-red-500"
                />
                <span>Show DNC</span>
              </label>
            </div>

            {/* Bulk actions */}
            {selectedLeadIds.length > 0 && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-400">{selectedLeadIds.length} selected:</span>
                <button
                  onClick={() => handleBulkStatus("shortlisted")}
                  disabled={bulkActionLoading}
                  className="px-2.5 py-1 bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 border border-indigo-700/60 rounded-md font-medium transition-colors"
                >
                  Shortlist
                </button>
                <button
                  onClick={() => handleBulkStatus("rejected")}
                  disabled={bulkActionLoading}
                  className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 rounded-md font-medium transition-colors"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="p-4 rounded-xl bg-red-950/50 border border-red-800 text-red-300 text-sm mb-6">
            {error}
          </div>
        )}

        {/* Leads Table */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-950/80 border-b border-gray-800 text-gray-400 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-3 px-4 w-10">
                    <input
                      type="checkbox"
                      onChange={handleSelectAll}
                      checked={leads.length > 0 && selectedLeadIds.length === leads.length}
                      className="rounded bg-gray-900 border-gray-800 text-indigo-600 focus:ring-indigo-500"
                    />
                  </th>
                  <th className="py-3 px-4">Score</th>
                  <th className="py-3 px-4">Business</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Rating</th>
                  <th className="py-3 px-4">Contact</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-gray-500">
                      <div className="flex items-center justify-center gap-2">
                        <span className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                        <span>Loading scored leads...</span>
                      </div>
                    </td>
                  </tr>
                ) : leads.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-gray-500">
                      No leads match the selected criteria.
                    </td>
                  </tr>
                ) : (
                  leads.map((lead) => {
                    const isSelected = selectedLeadIds.includes(lead.id);
                    const place = lead.place;
                    const isDNC = lead.status === "do_not_contact";

                    return (
                      <tr
                        key={lead.id}
                        className={`hover:bg-gray-800/40 transition-colors ${
                          isSelected ? "bg-indigo-950/20" : ""
                        }`}
                      >
                        <td className="py-3.5 px-4">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleSelect(lead.id)}
                            className="rounded bg-gray-900 border-gray-800 text-indigo-600 focus:ring-indigo-500"
                          />
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <span className="text-sm font-bold text-white font-mono">
                              {lead.final_score !== null ? Math.round(lead.final_score) : "--"}
                            </span>
                            <span className="text-[10px] text-gray-500">/100</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-medium text-white max-w-xs truncate">
                          <div>
                            <div className="font-semibold text-gray-100 truncate">
                              {place?.name || "Unknown"}
                            </div>
                            <div className="text-[11px] text-gray-400 truncate">
                              {place?.address || "No address"}
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-gray-300 capitalize whitespace-nowrap">
                          {place?.normalized_category || place?.category || "--"}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <div className="flex items-center gap-1 text-gray-300">
                            <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                            <span>{place?.rating ? place.rating.toFixed(1) : "--"}</span>
                            <span className="text-gray-500">({place?.review_count ?? 0})</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-gray-300 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {place?.email && (
                              <span title={place.email} className="text-indigo-400">
                                <Mail className="w-3.5 h-3.5" />
                              </span>
                            )}
                            {place?.website && (
                              <a
                                href={place.website}
                                target="_blank"
                                rel="noopener noreferrer"
                                title={place.website}
                                className="text-gray-400 hover:text-white"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span
                            className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                              isDNC
                                ? "bg-red-950/80 text-red-300 border border-red-800"
                                : lead.status === "contacted"
                                  ? "bg-blue-950/80 text-blue-300 border border-blue-800"
                                  : lead.status === "replied"
                                    ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                                    : "bg-gray-800 text-gray-300"
                            }`}
                          >
                            {lead.status.replace("_", " ").toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap">
                          <button
                            onClick={() => setSelectedLeadId(lead.id)}
                            className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-md font-medium text-xs inline-flex items-center gap-1 transition-colors"
                          >
                            <span>Open</span>
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Drawer */}
      {activeLead && (
        <LeadDrawer
          lead={activeLead}
          onClose={() => setSelectedLeadId(null)}
          onLeadUpdated={() => {
            fetchLeads();
          }}
        />
      )}
    </div>
  );
}
