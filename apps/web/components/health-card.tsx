"use client";

import { useEffect, useState } from "react";

type CheckStatus = "ok" | "error";

type CheckResult = {
  status: CheckStatus;
  latency_ms: number | null;
  detail: string | null;
};

type Health = {
  status: "ok" | "degraded";
  service: string;
  version: string;
  checks: Record<string, CheckResult>;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REFRESH_MS = 10_000;

export function HealthCard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${API_URL}/health`, {
          cache: "no-store",
          signal: controller.signal,
        });
        const body = (await response.json()) as Health;
        if (cancelled) return;
        setHealth(body);
        setError(null);
        setCheckedAt(new Date());
      } catch (err: unknown) {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
        setHealth(null);
        setError(`Could not reach the API at ${API_URL}. Is it running?`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    const interval = setInterval(() => void load(), REFRESH_MS);

    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(interval);
    };
  }, [refreshKey]);

  const healthy = health?.status === "ok";
  const dotClass =
    error || health?.status === "degraded"
      ? "bg-amber-500"
      : healthy
        ? "bg-emerald-500"
        : "bg-slate-300";

  return (
    <section
      aria-labelledby="health-heading"
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id="health-heading" className="text-lg font-semibold text-slate-900">
            System status
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Live check of the API, Postgres and Redis, refreshed every 10 seconds.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRefreshKey((key) => key + 1)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
        >
          {loading ? "Checking…" : "Refresh"}
        </button>
      </div>

      <div className="mt-5 flex items-center gap-2" aria-live="polite">
        <span className={`h-2.5 w-2.5 rounded-full ${dotClass}`} aria-hidden="true" />
        <span className="text-sm font-medium text-slate-800">
          {error
            ? "API unreachable"
            : health
              ? health.status === "ok"
                ? "All systems operational"
                : "Degraded: a dependency is unavailable"
              : "Checking…"}
        </span>
        {checkedAt ? (
          <span className="ml-auto text-xs text-slate-400">
            checked {checkedAt.toLocaleTimeString()}
          </span>
        ) : null}
      </div>

      {error ? (
        <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{error}</p>
      ) : null}

      {health ? (
        <dl className="mt-5 grid gap-3 sm:grid-cols-2">
          {Object.entries(health.checks).map(([name, check]) => (
            <div
              key={name}
              className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
            >
              <dt className="text-sm font-medium capitalize text-slate-700">{name}</dt>
              <dd className="flex items-center gap-2 text-sm">
                <span
                  className={`h-2 w-2 rounded-full ${check.status === "ok" ? "bg-emerald-500" : "bg-rose-500"}`}
                  aria-hidden="true"
                />
                <span className={check.status === "ok" ? "text-emerald-700" : "text-rose-700"}>
                  {check.status}
                </span>
                {check.latency_ms !== null ? (
                  <span className="text-slate-400">{check.latency_ms} ms</span>
                ) : null}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {health ? (
        <p className="mt-4 text-xs text-slate-400">
          {health.service} v{health.version}
        </p>
      ) : null}
    </section>
  );
}
