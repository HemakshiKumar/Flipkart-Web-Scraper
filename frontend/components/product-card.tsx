"use client";

import { motion, useReducedMotion } from "motion/react";
import { Star } from "lucide-react";

import { ProductLink } from "@/components/product-link";
import { ScoreMeter } from "@/components/score-meter";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatCount, formatPrice, formatRating } from "@/lib/format";
import type { Product } from "@/lib/types";

interface ProductCardProps {
  product: Product;
  index: number;
}

/** Mobile / tablet view of a single recommendation. */
export function ProductCard({ product, index }: ProductCardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.li
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.36,
        delay: reduceMotion ? 0 : index * 0.05,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      <Card className="bg-card transition-colors hover:border-foreground/30">
        <CardContent className="space-y-3.5 p-4 pt-4">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-sm font-bold leading-snug">{product.name}</h3>
            <Badge variant="mono" className="shrink-0 tabular-nums">
              #{index + 1}
            </Badge>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm">
            <span className="flex items-center gap-1.5 tabular-nums">
              <Star className="size-3.5 fill-current text-foreground/70" aria-hidden />
              {formatRating(product.rating)}
              {product.ratingsCount > 0 ? (
                <span className="text-xs text-muted-foreground">
                  ({formatCount(product.ratingsCount)})
                </span>
              ) : null}
            </span>
            <span className="font-medium tabular-nums">{formatPrice(product.price)}</span>
            <ScoreMeter
              score={product.score}
              similarity={product.similarity}
              index={index}
              className="ml-auto"
            />
          </div>

          {product.highlights.length > 0 ? (
            <ul className="flex flex-wrap gap-1.5">
              {product.highlights.map((highlight) => (
                <li key={highlight}>
                  <Badge variant="outline" className="font-normal">
                    {highlight}
                  </Badge>
                </li>
              ))}
            </ul>
          ) : null}

          <ProductLink product={product} variant="card" />
        </CardContent>
      </Card>
    </motion.li>
  );
}
