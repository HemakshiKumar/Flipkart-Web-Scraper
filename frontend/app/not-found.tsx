import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-4 px-5 py-24 text-center sm:px-8">
      <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">This page doesn&apos;t exist</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        The page you were looking for isn&apos;t here. Start a new product search instead.
      </p>
      <Button asChild className="mt-2">
        <Link href="/">Go to search</Link>
      </Button>
    </div>
  );
}
