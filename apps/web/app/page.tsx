import { HealthCard } from "@/components/health-card";

const services = [
  { name: "API", detail: "FastAPI on :8000", href: "http://localhost:8000/docs" },
  { name: "Scraper", detail: "gosom web UI on :8080", href: "http://localhost:8080" },
  { name: "Flower", detail: "added in Prompt 19", href: null },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-10 px-6 py-14">
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-sky-600">GapScout</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Where is the local market underserved?
        </h1>
        <p className="mt-3 max-w-2xl text-base text-slate-600">
          Map-based market intelligence: a hex-grid gap map for a city and category, plus a lead
          scorer that ranks the businesses worth pitching.
        </p>
      </header>

      <HealthCard />

      <section aria-labelledby="services-heading">
        <h2
          id="services-heading"
          className="text-sm font-semibold uppercase tracking-wide text-slate-500"
        >
          Local services
        </h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-3">
          {services.map((service) => (
            <li key={service.name} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="font-medium text-slate-900">{service.name}</p>
              {service.href ? (
                <a
                  className="mt-1 inline-block text-sm text-sky-700 underline-offset-2 hover:underline"
                  href={service.href}
                  target="_blank"
                  rel="noreferrer"
                >
                  {service.detail}
                </a>
              ) : (
                <p className="mt-1 text-sm text-slate-500">{service.detail}</p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <footer className="mt-auto border-t border-slate-200 pt-6 text-xs leading-relaxed text-slate-500">
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
