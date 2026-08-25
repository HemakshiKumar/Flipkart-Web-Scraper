import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link
          href="/"
          className="group flex items-center gap-2.5 rounded-md text-sm font-medium tracking-tight"
        >
          <span className="flex size-6 items-center justify-center rounded-md border border-border bg-surface-muted text-[0.65rem] font-semibold">
            PA
          </span>
          <span className="transition-colors group-hover:text-muted-foreground">ProductAI</span>
        </Link>

        <div className="flex items-center gap-3">
          <a
            href="https://web-scraper-ml.onrender.com/lab/workspaces/auto-6?reset=1"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden items-center gap-1.5 rounded-full border border-border/80 bg-surface-muted/60 px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground sm:inline-flex"
            title="Open Live ML JupyterLab Workspace"
          >
            <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
            ML Workspace
          </a>
          <a
            href="https://flipkart-web-scraper.onrender.com/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground sm:inline-flex"
            title="Open FastAPI Swagger API Docs"
          >
            API Docs
          </a>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
