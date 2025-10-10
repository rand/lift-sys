import { PropsWithChildren } from "react";

export function Card({ children, title }: PropsWithChildren<{ title?: string }>) {
  return (
    <section
      style={{
        background: "#1e293b",
        borderRadius: "1rem",
        padding: "1.5rem",
        boxShadow: "0 20px 45px rgba(15,23,42,0.35)",
      }}
    >
      {title && <h2 style={{ marginTop: 0 }}>{title}</h2>}
      {children}
    </section>
  );
}
