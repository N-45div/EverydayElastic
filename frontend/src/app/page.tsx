import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Search, Sparkles, Shield, Activity, CheckCircle2, Zap } from "lucide-react";

const features = [
  {
    title: "Elastic-Native Retrieval",
    description:
      "Blend semantic search with curated runbooks, tickets, and policy libraries to answer the questions ops teams ask every day.",
    Icon: Search,
  },
  {
    title: "Follow-Up Automation",
    description:
      "Post to Slack or tee up human review with a single click when the copilot suggests next actions.",
    Icon: Sparkles,
  },
  {
    title: "Enterprise Guardrails",
    description:
      "Ground every response in auditable sources with reranking and track decisions with built-in logging so compliance teams stay confident.",
    Icon: Shield,
  },
];

 

export default function Home() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-xl font-bold tracking-tight text-blue-600">
            EverydayElastic
          </Link>
          <div className="hidden items-center gap-8 text-sm text-gray-700 md:flex">
            <Link href="#features" className="hover:text-blue-600 transition-colors">
              Features
            </Link>
            <Link href="#use-cases" className="hover:text-blue-600 transition-colors">
              Use Cases
            </Link>
          </div>
          <Button asChild className="bg-blue-600 hover:bg-blue-700 text-white">
            <Link href="/copilot">Launch Copilot →</Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto flex max-w-7xl flex-col gap-20 px-6 py-16">
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-50 to-white border border-blue-200 px-12 py-20 shadow-xl">
          <div className="relative z-10 max-w-4xl mx-auto text-center space-y-8">
            <span className="inline-flex items-center rounded-full bg-blue-100 px-5 py-2 text-xs font-semibold uppercase tracking-wider text-blue-700">
              AI-Powered Ops Copilot
            </span>
            <h1 className="text-5xl font-bold leading-tight text-gray-900 sm:text-6xl">
              From Alert to Resolution in Minutes
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
              EverydayElastic orchestrates incident triage, retrieves runbooks, and suggests automated follow-ups. Built on Elasticsearch + Google Vertex AI with semantic search and smart reranking for ops teams.
            </p>
            <div className="flex flex-col gap-4 sm:flex-row justify-center items-center">
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-8" asChild>
                <Link href="/copilot">Try the Demo →</Link>
              </Button>
              <Button size="lg" variant="outline" className="border-blue-600 text-blue-600 hover:bg-blue-50 px-8" asChild>
                <Link href="#use-cases">See Use Cases</Link>
              </Button>
            </div>
          </div>
          <div className="absolute top-0 right-0 w-96 h-96 bg-blue-200/30 rounded-full blur-3xl -z-10" />
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-blue-300/20 rounded-full blur-3xl -z-10" />
        </section>

        <section id="features" className="grid gap-8 sm:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-blue-200 bg-blue-50/50 p-8 transition hover:border-blue-400 hover:shadow-lg"
            >
              <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-blue-200 bg-white text-blue-600">
                <feature.Icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <h2 className="text-xl font-bold text-blue-700 mb-2">
                {feature.title}
              </h2>
              <p className="text-sm text-gray-700 leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </section>

        <section id="use-cases" className="space-y-10">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">From Alert to Resolution</h2>
            <p className="text-lg text-gray-600">
              The copilot orchestrates every phase of your operations workflow—retrieving runbooks, summarizing impact, and queuing follow-up actions.
            </p>
          </div>
          <div className="space-y-6">
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-8">
              <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-blue-200 bg-white text-blue-700">
                <Activity className="h-5 w-5" aria-hidden="true" />
              </div>
              <h3 className="text-xl font-bold text-blue-700 mb-3">1. Detect & Scope</h3>
              <p className="text-gray-700 mb-4">
                Pull recent incident tickets, playbooks, and chat transcripts to understand severity, impacted services, and on-call owners.
              </p>
              <p className="text-sm text-blue-600 font-mono bg-white rounded-lg px-4 py-2">
                &quot;Show me Sev-1 incidents from the last 24 hours&quot;
              </p>
            </div>
            
            <div className="rounded-2xl border border-green-200 bg-green-50 p-8">
              <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-green-200 bg-white text-green-700">
                <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
              </div>
              <h3 className="text-xl font-bold text-green-700 mb-3">2. Recommend Actions</h3>
              <p className="text-gray-700 mb-4">
                Suggest Slack updates, policy reminders, or internal follow-ups backed by the evidence surfaced in the retrieval step.
              </p>
              <p className="text-sm text-green-600 font-mono bg-white rounded-lg px-4 py-2">
                &quot;What&apos;s the runbook for payment gateway timeout?&quot;
              </p>
            </div>
            
            <div className="rounded-2xl border border-orange-200 bg-orange-50 p-8">
              <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-orange-200 bg-white text-orange-700">
                <Zap className="h-5 w-5" aria-hidden="true" />
              </div>
              <h3 className="text-xl font-bold text-orange-700 mb-3">3. Automate Follow-Through</h3>
              <p className="text-gray-700 mb-4">
                Trigger webhooks or assign manual reviews with one click, keeping humans in the loop when judgment is required.
              </p>
              <p className="text-sm text-orange-600 font-mono bg-white rounded-lg px-4 py-2">
                Copilot suggests: &quot;Create Slack request&quot; → Click → Done ✓
              </p>
            </div>
          </div>
        </section>

        <section id="about" className="rounded-3xl border border-gray-200 bg-white p-10">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">About EverydayElastic</h2>
          <p className="text-gray-700 mb-4">
            EverydayElastic is an ops copilot that combines Elasticsearch semantic retrieval with Google Vertex AI reranking to deliver cited answers and actionable follow-ups. It keeps humans in the loop with clear sources and simple controls.
          </p>
          <ul className="grid gap-4 sm:grid-cols-2 text-gray-700">
            <li className="rounded-lg border border-gray-200 p-4">Semantic retrieval across runbooks, chat transcripts, policies, and docs.</li>
            <li className="rounded-lg border border-gray-200 p-4">Reranked results with citations and optional relevance scores.</li>
            <li className="rounded-lg border border-gray-200 p-4">Slack updates you can trigger directly from the chat.</li>
            <li className="rounded-lg border border-gray-200 p-4">Audit-friendly logs and explicit source references.</li>
          </ul>
        </section>

        <section className="rounded-3xl border border-blue-300 bg-gradient-to-br from-blue-600 to-blue-700 p-12 text-center text-white shadow-xl">
          <h2 className="text-4xl font-bold mb-4">
            Ready to Turn Elastic into Your Everyday Operations Copilot?
          </h2>
          <p className="mt-4 text-lg text-blue-100 max-w-2xl mx-auto">
            Launch the workspace demo to see how EverydayElastic triages incidents, enforces policy, and keeps teams aligned with semantic search + reranking.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button size="lg" className="bg-white text-blue-600 hover:bg-gray-100 px-8 font-semibold" asChild>
              <Link href="/copilot">Launch Demo Now →</Link>
            </Button>
            <Button variant="outline" size="lg" className="border-white text-white hover:bg-blue-500 px-8" asChild>
              <Link href="https://github.com/N-45div/EverydayElastic">View on GitHub</Link>
            </Button>
          </div>
        </section>
      </main>

      <footer className="border-t border-gray-200 bg-gray-50 py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 text-sm text-gray-600 sm:flex-row">
          <span>© {new Date().getFullYear()} EverydayElastic. Built with Elasticsearch + Google Cloud.</span>
          <div className="flex gap-6">
            <Link href="/copilot" className="hover:text-blue-600 transition-colors">
              Demo
            </Link>
            <Link href="#features" className="hover:text-blue-600 transition-colors">
              Features
            </Link>
            <Link href="#use-cases" className="hover:text-blue-600 transition-colors">
              Use Cases
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
