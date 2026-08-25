"use client";

import { ArrowUpRight, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Product } from "@/lib/types";

interface ProductLinkProps {
  product: Product;
  variant?: "row" | "card";
}

/**
 * Opens the original Flipkart page. Datasets scraped before the URL column
 * existed fall back to a Flipkart search for the exact product title, so the
 * action is never dead.
 */
export function ProductLink({ product, variant = "row" }: ProductLinkProps) {
  const href = product.url ?? product.searchUrl;
  const isDirect = Boolean(product.url);

  if (!href) return null;

  const button = (
    <Button
      variant={variant === "card" ? "outline" : "ghost"}
      size="sm"
      asChild
      className={variant === "card" ? "w-full" : "text-muted-foreground hover:text-foreground"}
    >
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer nofollow"
        aria-label={`${isDirect ? "View" : "Find"} ${product.name} on Flipkart (opens in a new tab)`}
      >
        {isDirect ? "View" : "Find"}
        {isDirect ? <ArrowUpRight aria-hidden /> : <Search aria-hidden />}
      </a>
    </Button>
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent>
        {isDirect
          ? "Open the Flipkart product page"
          : "This dataset has no stored link — opens a Flipkart search for this product"}
      </TooltipContent>
    </Tooltip>
  );
}
