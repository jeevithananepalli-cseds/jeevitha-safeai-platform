import { BackendStatus } from "@/components/BackendStatus";

const features = [
  { title: "SOS activation", body: "One-tap emergency that records an event and alerts your contacts." },
  { title: "Emergency contacts", body: "Manage the trusted people notified when you need help." },
  { title: "Location sharing", body: "Share and review your recent locations in real time." },
  { title: "AI risk assessment", body: "Intelligent scoring of how risky a place and time may be." },
];

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-10">
        <p className="text-sm font-medium uppercase tracking-wide text-emergency">
          SafeAI
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">
          Intelligent Women&apos;s Safety &amp; Emergency Response
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          An AI-powered platform to get help fast: SOS activation, trusted
          contacts, live location, and explainable risk assessment.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        {features.map((feature) => (
          <article
            key={feature.title}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="font-semibold">{feature.title}</h2>
            <p className="mt-1 text-sm text-slate-600">{feature.body}</p>
          </article>
        ))}
      </section>

      <footer className="mt-12 rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          System status
        </h2>
        <BackendStatus />
      </footer>
    </main>
  );
}
