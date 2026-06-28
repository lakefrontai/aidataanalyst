import Link from "next/link";
import { Rocket, BookOpen } from "lucide-react";

export default function CTA() {
  return (
    <section className="px-8 py-24 text-center bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
      <h2 className="text-3xl font-semibold mb-3">
        Start querying your data today
      </h2>
      <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-10">
        Open source. No subscription. Runs locally.
      </p>
      <div className="flex items-center justify-center gap-3 flex-wrap">
        <Link
          href="#setup"
          className="flex items-center gap-2 px-5 py-3 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Rocket size={14} />
          Get started
        </Link>
        <Link
          href="https://github.com/lakefrontai/aidataanalyst"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-5 py-3 rounded-lg border border-zinc-200 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
        >
          <BookOpen size={14} />
          Read the docs
        </Link>
      </div>
    </section>
  );
}
