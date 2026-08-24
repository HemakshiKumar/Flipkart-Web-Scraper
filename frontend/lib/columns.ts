/**
 * Column selection for the results table.
 *
 * The scraped datasets are not uniform - some searches carry review counts,
 * some carry battery specs, some carry neither. The table therefore derives its
 * optional columns from the rows it was given instead of hard-coding them.
 */

import type { Product } from "@/lib/types";

/** Attributes worth their own column, in priority order. */
const CANDIDATE_ATTRIBUTES = [
  "Battery life",
  "Bluetooth version",
  "Wireless range",
  "Charging time",
  "With Mic",
  "Connector type",
] as const;

/** An attribute earns a column when at least this share of rows has it. */
const COVERAGE_THRESHOLD = 0.6;

export interface DerivedColumns {
  /** Extra attribute column, or null when no attribute is common enough. */
  attribute: string | null;
  showReviews: boolean;
}

function attributeValue(product: Product, key: string): string | undefined {
  const match = Object.keys(product.attributes).find(
    (name) => name.toLowerCase() === key.toLowerCase(),
  );
  return match ? product.attributes[match] : undefined;
}

export function getAttributeValue(product: Product, key: string): string | undefined {
  return attributeValue(product, key);
}

export function deriveColumns(products: Product[]): DerivedColumns {
  if (products.length === 0) {
    return { attribute: null, showReviews: false };
  }

  const attribute =
    CANDIDATE_ATTRIBUTES.find((key) => {
      const covered = products.filter((product) => attributeValue(product, key)).length;
      return covered / products.length >= COVERAGE_THRESHOLD;
    }) ?? null;

  const showReviews = products.some((product) => product.ratingsCount > 0);

  return { attribute, showReviews };
}
