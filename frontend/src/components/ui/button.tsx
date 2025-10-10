import { ButtonHTMLAttributes, CSSProperties, DetailedHTMLProps } from "react";
import { clsx } from "clsx";

type Variant = "default" | "secondary" | "destructive" | "ghost" | "outline";

type Size = "sm" | "md";

type ButtonProps = DetailedHTMLProps<ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

const variantStyles: Record<Variant, string> = {
  default: "background-color: #6366f1; color: white;",
  secondary: "background-color: #1e293b; color: #e2e8f0;",
  destructive: "background-color: #ef4444; color: white;",
  ghost: "background-color: transparent; color: #e2e8f0;",
  outline: "background-color: transparent; border: 1px solid #6366f1; color: #6366f1;",
};

const sizeStyles: Record<Size, CSSProperties> = {
  sm: { padding: "0.35rem 0.75rem", fontSize: "0.85rem" },
  md: { padding: "0.6rem 1rem" },
};

export function Button({ variant = "default", size = "md", style, className, ...rest }: ButtonProps) {
  return (
    <button
      className={clsx("shadcn-button", className)}
      style={{
        borderRadius: "0.75rem",
        border: "none",
        fontWeight: 600,
        cursor: "pointer",
        ...parseStyleString(variantStyles[variant]),
        ...sizeStyles[size],
        ...style,
      }}
      {...rest}
    />
  );
}

function parseStyleString(input: string): CSSProperties {
  return input.split(";").reduce((acc, rule) => {
    const [property, value] = rule.split(":");
    if (!property || !value) return acc;
    const camelCase = property.trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    // @ts-ignore - indexing dynamic property
    acc[camelCase] = value.trim();
    return acc;
  }, {} as CSSProperties);
}
