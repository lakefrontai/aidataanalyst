const stats = [
  { value: "5+", label: "Databases supported" },
  { value: "100+", label: "Bedrock models" },
  { value: "Multi", label: "Simultaneous connections" },
  { value: "Free", label: "Open source" },
];

export default function Stats() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950">
      {stats.map((s, i) => (
        <div
          key={s.label}
          className={`py-6 px-5 text-center ${
            i < stats.length - 1
              ? "border-r border-zinc-200 dark:border-zinc-800"
              : ""
          }`}
        >
          <div className="text-2xl font-semibold text-blue-600">{s.value}</div>
          <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            {s.label}
          </div>
        </div>
      ))}
    </div>
  );
}
