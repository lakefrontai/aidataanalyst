import Link from "next/link";
import { ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer className="px-8 py-5 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 flex items-center justify-between flex-wrap gap-4">
      <span className="text-xs text-zinc-400">
        AI Data Analyst — open source under MIT
      </span>
      <div className="flex items-center gap-5">
        <Link
          href="https://github.com/lakefrontai/aidataanalyst"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
        >
          <ExternalLink size={13} />
          GitHub
        </Link>
        <span className="text-xs text-zinc-400">
          Streamlit · AWS Bedrock · pgvector
        </span>
      </div>
    </footer>
  );
}
