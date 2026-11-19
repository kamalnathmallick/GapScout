import Link from "next/link";
import { ArrowRight, Compass, LogIn, UserPlus } from "lucide-react";
import { HealthCard } from "@/components/health-card";

const services = [
  { name: "API", detail: "FastAPI on :8000", href: "http://localhost:8000/docs" },
  { name: "Scraper", detail: "gosom web UI on :8080", href: "http://localhost:8080" },
  { name: "Flower", detail: "added in Prompt 19", href: null },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-10 px-6 py-14">
      <header className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
            GapScout
          </p>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-800 bg-gray-900 text-xs font-medium text-gray-300 hover:text-white hover:bg-gray-800 transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Register</span>
            </Link>
          </div>
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Where is the local market underserved?
        </h1>
        <p className="max-w-2xl text-base text-gray-400">
          Map-based market intelligence: a hex-grid gap map for a city and category, plus a lead
          scorer that ranks the businesses worth pitching.
        </p>

        <div className="pt-2 flex flex-wrap gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-600/20"
          >
            <Compass className="w-4 h-4" />
            <span>Open Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/jobs/new"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-gray-800 bg-gray-900 hover:bg-gray-800 text-gray-300 font-medium text-sm transition-colors"
          >
            <span>Start Analysis</span>
          </Link>
        </div>
      </header>

      <HealthCard />

      <section aria-labelledby="services-heading">
        <h2
          id="services-heading"
          className="text-sm font-semibold uppercase tracking-wide text-gray-400"
        >
          Local services
        </h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-3">
          {services.map((service) => (
            <li key={service.name} className="rounded-xl border border-gray-800 bg-gray-900 p-4">
              <p className="font-medium text-white">{service.name}</p>
              {service.href ? (
                <a
                  className="mt-1 inline-block text-sm text-indigo-400 underline-offset-2 hover:underline"
                  href={service.href}
                  target="_blank"
                  rel="noreferrer"
                >
                  {service.detail}
                </a>
              ) : (
                <p className="mt-1 text-sm text-gray-500">{service.detail}</p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <footer className="mt-auto border-t border-gray-800 pt-6 text-xs leading-relaxed text-gray-500">
        <p>
          Scraping Google Maps may violate Google&apos;s Terms of Service. The bundled scraper
          provider is for learning and research only; switch to the official Places API provider
          before any commercial use.
        </p>
        <p className="mt-2">
          GapScout never sends outreach. It drafts messages; a human always sends them.
        </p>
      </footer>
    </main>
  );
}
