import { Database, Cpu, Brain, BarChart2, MessageSquare, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Feature {
  icon: LucideIcon;
  iconColor: string;
  title: string;
  desc: string;
}

const features: Feature[] = [
  {
    icon: Database,
    iconColor: "text-blue-500",
    title: "Multi-database",
    desc: "Connect to multiple databases simultaneously and switch between them in a single dropdown.",
  },
  {
    icon: Cpu,
    iconColor: "text-purple-500",
    title: "Any Bedrock model",
    desc: "Load all models available in your AWS account and pick the best fit — Mistral, Nova, Claude, and more.",
  },
  {
    icon: Brain,
    iconColor: "text-green-500",
    title: "pgvector schema search",
    desc: "Embed your schema with pgvector. Only relevant tables are sent to the model — cheaper and more accurate.",
  },
  {
    icon: BarChart2,
    iconColor: "text-amber-500",
    title: "Auto charts",
    desc: "Line, bar, scatter, and pie charts generated automatically based on the shape of your results.",
  },
  {
    icon: MessageSquare,
    iconColor: "text-blue-500",
    title: "Plain English answers",
    desc: "Every query returns a natural language summary highlighting key numbers, trends, and anomalies.",
  },
  {
    icon: ShieldCheck,
    iconColor: "text-zinc-400",
    title: "Read-only safe",
    desc: "Only SELECT queries are allowed. DROP, DELETE, UPDATE, and INSERT are blocked at the prompt level.",
  },
];

export default function Features() {
  return (
    <section
      id="features"
      className="px-8 py-20 bg-zinc-50 dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800"
    >
      <p className="text-xs font-semibold tracking-widest text-zinc-400 uppercase text-center mb-3">
        Features
      </p>
      <h2 className="text-3xl font-semibold text-center mb-14">
        Everything you need to query data faster
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 max-w-4xl mx-auto">
        {features.map((f) => {
          const Icon = f.icon;
          return (
            <div
              key={f.title}
              className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
            >
              <Icon size={22} className={`${f.iconColor} mb-3`} />
              <div className="text-sm font-semibold mb-2">{f.title}</div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                {f.desc}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
