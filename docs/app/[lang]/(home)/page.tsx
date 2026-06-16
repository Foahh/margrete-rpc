import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { gitConfig } from "@/lib/shared";

const githubUrl = `https://github.com/${gitConfig.user}/${gitConfig.repo}`;

type Copy = {
  description: string;
  getStarted: string;
  viewOnGitHub: string;
};

const dictionary: Record<string, Copy> = {
  en: {
    description: "Edit UMIGURI/Margrete charts programmatically with Python.",
    getStarted: "Get started",
    viewOnGitHub: "View on GitHub",
  },
  "zh-Hans": {
    description: "通过 Python 编辑 UMIGURI/Margrete 谱面",
    getStarted: "快速开始",
    viewOnGitHub: "在 GitHub 查看",
  },
};

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <path d="M12 .5C5.73.5.5 5.74.5 12.02c0 5.1 3.29 9.42 7.86 10.95.58.1.79-.25.79-.56v-2.1c-3.2.7-3.88-1.37-3.88-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.56-.29-5.25-1.28-5.25-5.7 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.43-2.69 5.41-5.26 5.69.41.36.78 1.08.78 2.18v3.23c0 .31.21.67.8.56A11.53 11.53 0 0 0 23.5 12.02C23.5 5.74 18.27.5 12 .5z" />
    </svg>
  );
}

export default async function HomePage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const t = dictionary[lang] ?? dictionary.en;

  return (
    <main className="flex flex-1 flex-col">
      {/* Hero */}
      <section className="border-fd-border relative overflow-hidden border-b">
        {/* decorative grid */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]"
          style={{
            backgroundImage:
              "linear-gradient(to right, color-mix(in oklch, var(--color-fd-border) 60%, transparent) 1px, transparent 1px), linear-gradient(to bottom, color-mix(in oklch, var(--color-fd-border) 60%, transparent) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
        {/* decorative glow */}
        <div
          aria-hidden
          className="bg-fd-primary/15 pointer-events-none absolute -top-40 left-1/2 size-[40rem] -translate-x-1/2 rounded-full blur-[120px]"
        />

        <div className="relative mx-auto flex max-w-5xl flex-col items-center px-6 py-24 text-center sm:py-32">
          <h1 className="from-fd-foreground to-fd-foreground/55 max-w-3xl bg-gradient-to-b bg-clip-text pb-2 text-5xl font-bold tracking-tight text-transparent sm:text-6xl">
            Margrete RPC
          </h1>

          <p className="text-fd-muted-foreground mt-6 max-w-2xl text-lg">{t.description}</p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link
              href={`/${lang}/docs`}
              className={cn(buttonVariants({ color: "primary" }), "h-11 gap-2 px-6 text-base")}
            >
              {t.getStarted}
              <ArrowRight className="size-4" />
            </Link>
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className={cn(buttonVariants({ color: "outline" }), "h-11 gap-2 px-6 text-base")}
            >
              <GitHubIcon className="size-4" />
              {t.viewOnGitHub}
            </a>
          </div>

          {/* Code preview */}
          <div className="mt-16 w-full max-w-2xl text-left">
            <div className="border-fd-border bg-fd-card/70 shadow-fd-primary/5 overflow-hidden rounded-xl border shadow-2xl backdrop-blur">
              <div className="border-fd-border flex items-center gap-2 border-b px-4 py-3">
                <span className="size-3 rounded-full bg-red-400/80" />
                <span className="size-3 rounded-full bg-yellow-400/80" />
                <span className="size-3 rounded-full bg-green-400/80" />
                <span className="text-fd-muted-foreground ml-2 font-mono text-xs">example.py</span>
              </div>
              <pre className="overflow-x-auto p-5 font-mono text-sm leading-relaxed">
                <code>
                  <span className="text-fd-muted-foreground">from</span> margrete_rpc{" "}
                  <span className="text-fd-muted-foreground">import</span> Margrete
                  {"\n"}
                  <span className="text-fd-muted-foreground">
                    from
                  </span> margrete_rpc.chart.notes{" "}
                  <span className="text-fd-muted-foreground">import</span> Tap
                  {"\n\n"}m = <span className="text-fd-primary">Margrete</span>()
                  <span className="text-fd-muted-foreground"> # auto-detect the plugin</span>
                  {"\n"}
                  <span className="text-fd-muted-foreground">with</span> m.
                  <span className="text-fd-primary">open_edit</span>(
                  <span className="text-green-600 dark:text-green-400">&quot;add a tap&quot;</span>){" "}
                  <span className="text-fd-muted-foreground">as</span> tx:
                  {"\n"}
                  {"    "}tx.chart.notes.<span className="text-fd-primary">append</span>(
                  <span className="text-fd-primary">Tap</span>(t=
                  <span className="text-amber-600 dark:text-amber-400">0</span>, x=
                  <span className="text-amber-600 dark:text-amber-400">0</span>, w=
                  <span className="text-amber-600 dark:text-amber-400">4</span>))
                  {"\n"}
                  <span className="text-fd-muted-foreground"># applied atomically on exit</span>
                </code>
              </pre>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
