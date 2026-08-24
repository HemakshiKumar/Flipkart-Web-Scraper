import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { BackgroundGrid } from "@/components/background-grid";
import { SiteHeader } from "@/components/site-header";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "ProductAI — Intelligent product discovery",
    template: "%s — ProductAI",
  },
  description:
    "Search Flipkart in plain English and get products ranked by a TF-IDF recommendation engine.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafafa" },
    { media: "(prefers-color-scheme: dark)", color: "#0f0f0f" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider>
            <BackgroundGrid />
            <SiteHeader />
            <main className="flex flex-1 flex-col">{children}</main>
            <footer className="border-t border-border/60 py-6">
              <div className="mx-auto flex w-full max-w-6xl flex-col gap-1 px-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-8">
                <span>Powered by the repository&apos;s scraping + TF-IDF recommendation engine.</span>
                <span className="font-mono text-[0.7rem]">scrape → clean → vectorise → rank</span>
              </div>
            </footer>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
