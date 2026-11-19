"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Settings as SettingsIcon,
  Download,
  Trash2,
  Building,
  User,
  Shield,
  Loader2,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { UserOut } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const { data: user, isLoading } = useQuery<UserOut>({
    queryKey: ["me"],
    queryFn: () => api.getMe(),
  });

  const handleExportData = async () => {
    setIsExporting(true);
    setExportSuccess(false);
    try {
      const data = await api.exportAccountData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `gapscout-export-${user?.workspace?.name || "data"}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 4000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to export account data");
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteData = async () => {
    if (confirmText !== "DELETE") {
      setDeleteError("Please type DELETE to confirm");
      return;
    }

    if (
      !window.confirm(
        "Are you absolutely sure? This will delete all search jobs, places, hex metrics, leads, and outreach events for your workspace.",
      )
    ) {
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteAccountData();
      api.clearAuth();
      router.push("/login");
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete account data");
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6 sm:p-10">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <SettingsIcon className="w-7 h-7 text-indigo-400" />
            Workspace Settings
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage your account, tenant isolation, and DPDP / GDPR data controls.
          </p>
        </div>

        {/* Profile Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 sm:p-8 space-y-6">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <User className="w-5 h-5 text-indigo-400" />
            <span>Profile & Workspace</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
            <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
              <span className="text-xs text-gray-500 block mb-1">Email</span>
              <span className="font-medium text-white">{user?.email}</span>
            </div>

            <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
              <span className="text-xs text-gray-500 block mb-1">Full Name</span>
              <span className="font-medium text-white">{user?.full_name || "Not set"}</span>
            </div>

            <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
              <span className="text-xs text-gray-500 block mb-1 flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-gray-400" />
                Workspace
              </span>
              <span className="font-medium text-white">{user?.workspace?.name}</span>
              <span className="text-[11px] text-gray-500 block font-mono mt-0.5">
                ID: {user?.workspace?.id}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-gray-950 border border-gray-800">
              <span className="text-xs text-gray-500 block mb-1 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-gray-400" />
                Role & Isolation
              </span>
              <span className="font-medium text-emerald-400 capitalize">
                {user?.role || "Member"} (Tenant Isolated)
              </span>
            </div>
          </div>
        </div>

        {/* Data Portability (Export) */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 sm:p-8 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Download className="w-5 h-5 text-indigo-400" />
            <span>Data Portability (Export)</span>
          </h2>
          <p className="text-sm text-gray-400">
            Download a full JSON dump of your workspace data, including all search jobs, scraped and
            cleaned places, hex metrics, leads, and outreach events.
          </p>

          <div className="pt-2">
            <button
              onClick={handleExportData}
              disabled={isExporting}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors disabled:opacity-50"
            >
              {isExporting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Generating export...</span>
                </>
              ) : exportSuccess ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-300" />
                  <span>Downloaded!</span>
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  <span>Export All Workspace Data</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Danger Zone (Data Deletion) */}
        <div className="bg-red-950/20 border border-red-500/20 rounded-2xl p-6 sm:p-8 space-y-4">
          <h2 className="text-base font-semibold text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span>Danger Zone: Right to be Forgotten</span>
          </h2>
          <p className="text-sm text-gray-400 leading-relaxed">
            Permanently delete all business data, places, hex metrics, leads, outreach history, and
            search jobs associated with this workspace. This action cannot be undone.
          </p>

          {deleteError && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
              {deleteError}
            </div>
          )}

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="Type DELETE to confirm"
              className="px-4 py-2 rounded-xl bg-gray-950 border border-gray-800 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-red-500"
            />
            <button
              onClick={handleDeleteData}
              disabled={isDeleting || confirmText !== "DELETE"}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-medium text-sm transition-colors disabled:opacity-50"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Deleting workspace data...</span>
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  <span>Permanently Delete Data</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
