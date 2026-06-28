const databases = [
  { emoji: "❄️", name: "Snowflake", sub: "Cloud data warehouse" },
  { emoji: "🐘", name: "AWS RDS PostgreSQL", sub: "SSL + fully managed" },
  { emoji: "💻", name: "Local PostgreSQL", sub: "On-prem or localhost" },
  { emoji: "🐬", name: "MySQL / Aurora", sub: "MySQL & Aurora MySQL" },
];

export default function Databases() {
  return (
    <section
      id="databases"
      className="px-8 py-20 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800"
    >
      <p className="text-xs font-semibold tracking-widest text-zinc-400 uppercase text-center mb-3">
        Supported databases
      </p>
      <h2 className="text-3xl font-semibold text-center mb-12">
        Works with your stack
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
        {databases.map((db) => (
          <div
            key={db.name}
            className="flex flex-col items-center text-center gap-3 p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
          >
            <span className="text-3xl" role="img" aria-label={db.name}>
              {db.emoji}
            </span>
            <div>
              <div className="text-sm font-medium">{db.name}</div>
              <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">
                {db.sub}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
