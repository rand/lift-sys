import { cn } from "@/lib/utils";

interface SkipLinkProps {
  href: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * SkipLink - Accessibility component for keyboard navigation
 *
 * Allows keyboard users to skip directly to main content areas.
 * Hidden by default, becomes visible when focused via Tab key.
 *
 * @example
 * <SkipLink href="#main-content">Skip to main content</SkipLink>
 * <SkipLink href="#navigation">Skip to navigation</SkipLink>
 */
export function SkipLink({ href, children, className }: SkipLinkProps) {
  return (
    <a
      href={href}
      className={cn(
        // Position off-screen by default
        "absolute left-0 top-0 -translate-y-full",
        // Style when visible
        "z-50 bg-brand text-brand-foreground px-4 py-2 rounded-md",
        "font-semibold text-sm shadow-lg",
        // Show on focus
        "focus:translate-y-2 focus:translate-x-2",
        "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        // Smooth transition
        "transition-transform duration-200 ease-smooth",
        className
      )}
    >
      {children}
    </a>
  );
}
