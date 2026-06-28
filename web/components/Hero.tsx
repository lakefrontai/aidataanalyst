import Link from "next/link";
import { Play, ExternalLink } from "lucide-react";

export default function Hero() {
  return (
    <section className="px-8 py-24 text-center bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
      <h1 className="text-5xl font-semibold leading-tight max-w-2xl mx-auto mb-5 tracking-tight">
        Ask your data anything.{" "}
        <span className="text-blue-600">Get SQL, charts, and answers.</span>
      </h1>
      <p className="text-lg text-zinc-500 dark:text-zinc-400 max-w-md mx-auto mb-10 leading-relaxed">
        Connect any database, pick any Bedrock model, and query in plain
        English. No SQL required.
      </p>

      <div className="flex items-center justify-center gap-3 flex-wrap mb-16">
        <Link
          href="#setup"
          className="flex items-center gap-2 px-5 py-3 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Play size={14} />
          Get started
        </Link>
        <Link
          href="https://github.com/lakefrontai/aidataanalyst"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-5 py-3 rounded-lg border border-zinc-200 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
        >
          <ExternalLink size={14} />
          View on GitHub
        </Link>
      </div>

      {/* Terminal mockup */}
      <div className="max-w-lg mx-auto rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden text-left bg-zinc-50 dark:bg-zinc-950">
        <div className="flex items-center gap-1.5 px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
          <span className="w-3 h-3 rounded-full bg-red-400" />
          <span className="w-3 h-3 rounded-full bg-amber-400" />
          <span className="w-3 h-3 rounded-full bg-green-400" />
          <span className="ml-3 text-xs text-zinc-400">terminal</span>
        </div>
        <div className="px-5 py-4 font-mono text-xs leading-loose text-zinc-500 dark:text-zinc-400">
          <div>
            <span className="text-zinc-400">$</span>{" "}
            <span className="text-blue-500">pip install</span> -r
            requirements.txt
          </div>
          <div>
            <span className="text-zinc-400">$</span>{" "}
            <span className="text-blue-500">streamlit run</span> app.py
          </div>
          <div className="mt-1 text-green-500">
            ✓ Local URL: http://localhost:8501
          </div>
        </div>
      </div>
    </section>
  );
}
