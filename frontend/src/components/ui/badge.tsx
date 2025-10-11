import { PropsWithChildren } from "react";

const variants = {
  info: "#6366f1",
  success: "#10b981",
  warning: "#f59e0b",
  error: "#ef4444",
  secondary: "#334155",
};

type Variant = keyof typeof variants;

export function Badge({ children, variant = "info" }: PropsWithChildren<{ variant?: Variant }>) {
  return (
    <span
      style={{
        backgroundColor: variants[variant],
        color: "white",
        borderRadius: "999px",
        padding: "0.2rem 0.75rem",
        fontSize: "0.75rem",
        fontWeight: 600,
      }}
    >
      {children}
    </span>
  );
}
