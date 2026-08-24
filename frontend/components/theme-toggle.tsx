"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/**
 * Day/night toggle.
 *
 * The two icons are always rendered and cross-fade purely in CSS, driven by the
 * `dark` class next-themes puts on <html>. That keeps the server and client
 * markup identical (no hydration mismatch, no theme flash) while still giving
 * the swap a smooth animated transition.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          aria-label="Toggle between light and dark mode"
          className="relative text-muted-foreground hover:text-foreground"
        >
          <Sun
            aria-hidden
            className="size-4 rotate-0 scale-100 transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] dark:-rotate-90 dark:scale-0"
          />
          <Moon
            aria-hidden
            className="absolute size-4 rotate-90 scale-0 transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] dark:rotate-0 dark:scale-100"
          />
        </Button>
      </TooltipTrigger>
      <TooltipContent>Toggle theme</TooltipContent>
    </Tooltip>
  );
}
