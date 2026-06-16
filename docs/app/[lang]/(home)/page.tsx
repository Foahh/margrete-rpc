import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { ServerCodeBlock } from "fumadocs-ui/components/codeblock.rsc";

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
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      fill="currentColor"
      className={className}
      viewBox="0 0 16 16"
    >
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8" />
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
            <ServerCodeBlock
              lang="python"
              code={`\
from margrete_rpc import Margrete
from margrete_rpc.chart.notes import Tap

m = Margrete()  # auto-detect the plugin
with m.open_edit() as tx:
    tx.chart.notes.append(Tap(t=0, x=0, w=4))
# applied atomically on exit`}
              codeblock={{
                title: "example.py",
                className: "my-0 bg-fd-card/70 shadow-2xl shadow-fd-primary/5 backdrop-blur",
              }}
            />
          </div>
        </div>
      </section>
    </main>
  );
}
