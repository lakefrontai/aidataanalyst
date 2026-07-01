import { redirect } from "next/navigation";
import { BarChart2 } from "lucide-react";
import { auth } from "@/auth";
import SignOutButton from "@/components/SignOutButton";

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login");
  }

  return (
    <div className="flex-1 flex flex-col bg-white dark:bg-zinc-900">
      <nav className="flex items-center justify-between px-8 py-4 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <BarChart2 size={17} className="text-white" />
          </div>
          <span className="font-semibold text-sm">MyDataTalk</span>
        </div>
        <SignOutButton />
      </nav>

      <div className="flex-1 flex items-center justify-center px-8 py-24 text-center">
        <div>
          <h1 className="text-2xl font-semibold mb-2">
            Welcome{session.user.name ? `, ${session.user.name}` : ""}
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-sm mx-auto">
            You&apos;re signed in as {session.user.email}. The hosted MyDataTalk
            cloud analyst is coming soon — for now, run the app locally from{" "}
            <a
              href="https://github.com/lakefrontai/aidataanalyst"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              GitHub
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
