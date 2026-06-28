import Link from "next/link";
import { BarChart2, ExternalLink } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between px-8 py-4 bg-white/80 dark:bg-zinc-900/80 backdrop-blur border-b border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
          <BarChart2 size={17} className="text-white" />
        </div>
        <span className="font-semibold text-sm">AI Data Analyst</span>
      </div>

      <div className="hidden md:flex items-center gap-1">
        <Link href="#features" className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 px-3 py-2 rounded-md transition-colors">
          Features
        </Link>
        <Link href="#databases" className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 px-3 py-2 rounded-md transition-colors">
          Databases
        </Link>
        <Link href="#setup" className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 px-3 py-2 rounded-md transition-colors">
          Setup
        </Link>
        <Link
          href="https://github.com/lakefrontai/aidataanalyst"
          target="_blank"
          rel="noopener noreferrer"
          className="ml-2 flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
        >
          <ExternalLink size={14} />
          GitHub
        </Link>
      </div>
    </nav>
  );
}
