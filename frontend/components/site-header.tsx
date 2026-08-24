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

        <div className="flex items-center gap-1">
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Flipkart recommendation engine
          </span>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
