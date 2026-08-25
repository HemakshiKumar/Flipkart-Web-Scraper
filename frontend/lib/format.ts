/** Display helpers shared by the table and the mobile cards. */

const priceFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const compactFormatter = new Intl.NumberFormat("en-IN", { notation: "compact" });

export function formatPrice(value: number): string {
  return priceFormatter.format(value);
}

export function formatCount(value: number): string {
  return compactFormatter.format(value);
}

export function formatRating(value: number): string {
  return value > 0 ? value.toFixed(1) : "—";
}

export function formatScore(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDuration(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** Split free-text requirements into chips for the results header. */
export function splitRequirements(requirements: string): string[] {
  return requirements
    .split(/[,;]|\band\b/gi)
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

export const SOURCE_LABELS: Record<string, { label: string; description: string }> = {
  live: {
    label: "Live scrape",
    description: "Products were scraped from Flipkart for this search.",
  },
  cache: {
    label: "Cached scrape",
    description: "Reused a recent scrape of this search instead of hitting Flipkart again.",
  },
  seed: {
    label: "Stored dataset",
    description:
      "Live scraping was unavailable, so the dataset stored in the repository was ranked instead.",
  },
};
