import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-5 py-14 sm:px-8">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}
