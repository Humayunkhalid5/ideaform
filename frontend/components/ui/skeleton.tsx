import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-lg bg-line/50", className)}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-surface/70 to-transparent" />
    </div>
  );
}

export function PageSkeleton({ cards = 3 }: { cards?: number }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2.5">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-8 w-64 max-w-full" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: cards }).map((_, index) => (
          <Skeleton key={index} className="h-44 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
