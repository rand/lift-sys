import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";

export function AuthCallbackView() {
  const { refresh } = useAuth();
  const [status, setStatus] = useState<"pending" | "success" | "error">("pending");

  useEffect(() => {
    void refresh()
      .then(() => {
        setStatus("success");
        window.location.replace("/");
      })
      .catch(() => {
        setStatus("error");
      });
  }, [refresh]);

  return (
    <div
      className="main-shell"
      style={{
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: "0.75rem",
      }}
    >
      <p>{status === "error" ? "We couldn't complete the sign-in." : "Completing sign-in…"}</p>
      {status === "error" && <a href="/">Return home</a>}
    </div>
  );
}
