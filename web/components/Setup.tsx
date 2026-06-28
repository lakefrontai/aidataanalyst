const steps = [
  {
    n: "1",
    color: "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 text-blue-600",
    title: "Clone and install",
    content: (
      <div className="mt-3 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 px-4 py-3 font-mono text-xs leading-loose text-zinc-500 dark:text-zinc-400">
        <div>git clone https://github.com/lakefrontai/aidataanalyst</div>
        <div>pip install -r requirements.txt</div>
      </div>
    ),
  },
  {
    n: "2",
    color: "bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800 text-purple-600",
    title: "Add AWS credentials",
    content: (
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
        Create an IAM user with{" "}
        <code className="bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-xs">
          AmazonBedrockFullAccess
        </code>
        , generate an access key, and paste it into the Connections tab.
      </p>
    ),
  },
  {
    n: "3",
    color: "bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800 text-green-600",
    title: "Connect your database",
    content: (
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
        Pick a database type from the dropdown, give it a name, fill in
        credentials, and click Connect. Add as many as you need.
      </p>
    ),
  },
  {
    n: "4",
    color: "bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800 text-amber-600",
    title: "Ask anything",
    content: (
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
        Switch to the Chat tab, type a question in plain English, and get SQL, a
        results table, a chart, and a summary.
      </p>
    ),
  },
];

export default function Setup() {
  return (
    <section
      id="setup"
      className="px-8 py-20 bg-zinc-50 dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800"
    >
      <p className="text-xs font-semibold tracking-widest text-zinc-400 uppercase text-center mb-3">
        Setup
      </p>
      <h2 className="text-3xl font-semibold text-center mb-14">
        Up and running in 4 steps
      </h2>

      <div className="max-w-xl mx-auto flex flex-col gap-0">
        {steps.map((step, i) => (
          <div key={step.n} className="flex gap-5">
            {/* timeline */}
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className={`w-9 h-9 rounded-full border flex items-center justify-center text-sm font-semibold flex-shrink-0 ${step.color}`}
              >
                {step.n}
              </div>
              {i < steps.length - 1 && (
                <div className="w-px flex-1 bg-zinc-200 dark:bg-zinc-800 my-2" />
              )}
            </div>
            {/* content */}
            <div className={`pb-10 pt-1 flex-1 ${i === steps.length - 1 ? "pb-0" : ""}`}>
              <div className="text-sm font-semibold">{step.title}</div>
              {step.content}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
