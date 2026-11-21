import Link from "next/link";
import {
  ArrowRight,
  Compass,
  LogIn,
  UserPlus,
  MapPin,
  Sparkles,
  BarChart2,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { HealthCard } from "@/components/health-card";

const services = [
  { name: "API", detail: "FastAPI on :8000", href: "http://localhost:8000/docs" },
  { name: "Scraper", detail: "gosom web UI on :8080", href: "http://localhost:8080" },
  { name: "Flower", detail: "Celery task monitor", href: null },
];

export default function HomePage() {
  return (
    <div className="flex-1 max-w-6xl mx-auto w-full px-6 py-10 space-y-10">
      {/* Hero Header */}
      <header className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400 font-mono">
              Market Intelligence System
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors shadow-sm shadow-indigo-600/30"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Register</span>
            </Link>
          </div>
        </div>

        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
          Where is the local market <span className="text-indigo-400">underserved</span>?
        </h1>
        <p className="max-w-2xl text-sm sm:text-base text-slate-400 leading-relaxed">
          Map-based market intelligence: an H3 hexagonal grid gap map identifying saturated versus
          unserved zones, plus an active-learning lead scorer ranking the businesses worth pitching.
        </p>

        <div className="pt-2 flex flex-wrap gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs sm:text-sm transition-all shadow-lg shadow-indigo-600/25 hover:scale-[1.01]"
          >
            <Compass className="w-4 h-4" />
            <span>Open Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/jobs/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-slate-300 font-semibold text-xs sm:text-sm transition-colors"
          >
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span>Start Analysis</span>
          </Link>
        </div>
      </header>

      {/* Feature Value Props Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-xl space-y-2 border border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <MapPin className="w-4 h-4" />
          </div>
          <h2 className="text-sm font-semibold text-white">H3 Geospatial Gap Engine</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Hexagonal spatial analysis measuring competitor supply against office and residential
            demand anchors.
          </p>
        </div>

        <div className="glass-panel p-5 rounded-xl space-y-2 border border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <BarChart2 className="w-4 h-4" />
          </div>
          <h2 className="text-sm font-semibold text-white">Rule + ML Blended Scoring</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Pain, fit, timing, and reachability scoring with active learning to prioritize
            high-yield commercial outreach.
          </p>
        </div>

        <div className="glass-panel p-5 rounded-xl space-y-2 border border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h2 className="text-sm font-semibold text-white">Grounded Draft Outreach</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Draft-only messaging workflow with zero automated sending, strict DNC protection, and
            mandatory opt-out guarantees.
          </p>
        </div>
      </div>

      <HealthCard />

      {/* Local Infrastructure Services */}
      <section aria-labelledby="services-heading" className="space-y-3">
        <h2
          id="services-heading"
          className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono"
        >
          Active Monorepo Services
        </h2>
        <ul className="grid gap-3 sm:grid-cols-3">
          {services.map((service) => (
            <li
              key={service.name}
              className="glass-panel rounded-xl border border-slate-800/80 p-4"
            >
              <div className="flex items-center justify-between">
                <p className="font-semibold text-white text-xs">{service.name}</p>
                <Zap className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              {service.href ? (
                <a
                  className="mt-1 inline-block text-xs text-indigo-400 hover:text-indigo-300 underline-offset-2 hover:underline font-mono"
                  href={service.href}
                  target="_blank"
                  rel="noreferrer"
                >
                  {service.detail}
                </a>
              ) : (
                <p className="mt-1 text-xs text-slate-500 font-mono">{service.detail}</p>
              )}
            </li>
          ))}
        </ul>
      </section>

      {/* Footer Notes */}
      <footer className="mt-auto border-t border-slate-800/80 pt-6 text-[11px] leading-relaxed text-slate-500 space-y-1.5 font-mono">
        <p>
          Scraping Google Maps may violate Google&apos;s Terms of Service. The bundled scraper
          provider is for learning and research only; switch to the official Places API provider
          before commercial usage.
        </p>
        <p>
          GapScout never sends outreach automatically. It drafts grounded messages; a human sends
          them.
        </p>
      </footer>
    </div>
  );
}
