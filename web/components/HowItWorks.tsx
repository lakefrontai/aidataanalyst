import { ArrowRight } from "lucide-react";

const steps = [
  {
    n: "1",
    color: "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 text-blue-600",
    title: "Ask a question",
    desc: '"How many disputes opened last week?"',
  },
  {
    n: "2",
    color: "bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800 text-purple-600",
    title: "SQL is generated",
    desc: "Bedrock model writes and runs the query",
  },
  {
    n: "3",
    color: "bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800 text-green-600",
    title: "Chart and summary",
    desc: "Auto chart + plain English answer",
  },
];

export default function HowItWorks() {
  return (
    <section className="px-8 py-20 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
      <p className="text-xs font-semibold tracking-widest text-zinc-400 uppercase text-center mb-3">
        How it works
      </p>
      <h2 className="text-3xl font-semibold text-center mb-14">
        From question to insight in seconds
      </h2>

      <div className="flex flex-col md:flex-row items-center justify-center gap-4 max-w-3xl mx-auto">
        {steps.map((step, i) => (
          <div key={step.n} className="flex items-center gap-4 w-full md:w-auto">
            <div className="flex-1 md:w-52 text-center bg-zinc-50 dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 p-6">
              <div
                className={`w-10 h-10 rounded-full border flex items-center justify-center mx-auto mb-4 text-sm font-semibold ${step.color}`}
              >
                {step.n}
              </div>
              <div className="text-sm font-medium mb-1">{step.title}</div>
              <div className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                {step.desc}
              </div>
            </div>
            {i < steps.length - 1 && (
              <ArrowRight
                size={18}
                className="text-zinc-300 dark:text-zinc-600 hidden md:block flex-shrink-0"
              />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
