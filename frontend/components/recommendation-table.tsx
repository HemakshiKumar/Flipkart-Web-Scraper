"use client";

import { motion, useReducedMotion } from "motion/react";
import { Star } from "lucide-react";

import { ProductLink } from "@/components/product-link";
import { ScoreMeter } from "@/components/score-meter";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { deriveColumns, getAttributeValue } from "@/lib/columns";
import { formatCount, formatPrice, formatRating } from "@/lib/format";
import type { Product } from "@/lib/types";

interface RecommendationTableProps {
  products: Product[];
}

/** Desktop view. The mobile view uses `ProductCard` instead. */
export function RecommendationTable({ products }: RecommendationTableProps) {
  const reduceMotion = useReducedMotion();
  const columns = deriveColumns(products);

  return (
    <div className="overflow-hidden rounded-xl border border-border/80 bg-card">
      <Table>
        <caption className="sr-only">
          Recommended products ranked by relevance, with rating, price and score.
        </caption>
        <TableHeader>
          <TableRow className="border-border">
            <TableHead className="w-12 pl-5">#</TableHead>
            <TableHead>Product</TableHead>
            {columns.attribute ? (
              <TableHead className="hidden lg:table-cell">{columns.attribute}</TableHead>
            ) : null}
            <TableHead className="w-28">Rating</TableHead>
            <TableHead className="w-28 text-right">Price</TableHead>
            <TableHead className="w-32">Score</TableHead>
            <TableHead className="w-24 pr-5 text-right">
              <span className="sr-only">Open on Flipkart</span>
              Link
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {products.map((product, index) => (
            <motion.tr
              key={`${product.name}-${index}`}
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.36,
                delay: reduceMotion ? 0 : index * 0.045,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="group border-b border-border/60 transition-colors last:border-0 hover:bg-accent/40"
            >
              <TableCell className="pl-5 text-xs text-muted-foreground tabular-nums">
                {String(index + 1).padStart(2, "0")}
              </TableCell>

              <TableCell className="max-w-sm">
                <p className="line-clamp-2 font-bold leading-snug">{product.name}</p>
                {product.highlights.length > 0 ? (
                  <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                    {product.highlights.join(" · ")}
                  </p>
                ) : null}
              </TableCell>

              {columns.attribute ? (
                <TableCell className="hidden text-sm text-muted-foreground lg:table-cell">
                  {getAttributeValue(product, columns.attribute) ?? "—"}
                </TableCell>
              ) : null}

              <TableCell>
                <span className="flex items-center gap-1.5 text-sm tabular-nums">
                  <Star className="size-3.5 fill-current text-foreground/70" aria-hidden />
                  {formatRating(product.rating)}
                </span>
                {columns.showReviews && product.ratingsCount > 0 ? (
                  <span className="text-xs text-muted-foreground">
                    {formatCount(product.ratingsCount)} ratings
                  </span>
                ) : null}
              </TableCell>

              <TableCell className="text-right font-medium tabular-nums">
                {formatPrice(product.price)}
              </TableCell>

              <TableCell>
                <ScoreMeter score={product.score} similarity={product.similarity} index={index} />
              </TableCell>

              <TableCell className="pr-5 text-right">
                <ProductLink product={product} />
              </TableCell>
            </motion.tr>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
