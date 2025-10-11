import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Skeleton loading component for placeholder content
 *
 * @example
 * <Skeleton className="h-4 w-[250px]" />
 * <Skeleton className="h-12 w-12 rounded-full" />
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg bg-secondary transition-colors duration-200 ease-smooth",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
