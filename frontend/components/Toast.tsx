"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

export type ToastType = "error" | "warning" | "info" | "success";

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType, title?: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = "error", title?: string) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastItem = { id, type, title, message };

      setToasts((prev) => [...prev.slice(-4), newToast]); // max 5 visible

      // Auto dismiss after 6s
      setTimeout(() => {
        removeToast(id);
      }, 6000);
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: "fixed",
          bottom: "var(--sp-6)",
          right: "var(--sp-6)",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-3)",
          maxWidth: 420,
          width: "calc(100vw - 32px)",
          pointerEvents: "none",
        }}
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            style={{
              pointerEvents: "auto",
              padding: "var(--sp-4) var(--sp-5)",
              borderRadius: "var(--r-xl)",
              background:
                toast.type === "error"
                  ? "#fef2f2"
                  : toast.type === "warning"
                  ? "#fffbeb"
                  : toast.type === "success"
                  ? "#f0fdf4"
                  : "var(--brand-50)",
              border: `1.5px solid ${
                toast.type === "error"
                  ? "#fca5a5"
                  : toast.type === "warning"
                  ? "#fde68a"
                  : toast.type === "success"
                  ? "#bbf7d0"
                  : "var(--brand-200)"
              }`,
              boxShadow: "var(--shadow-lg)",
              color:
                toast.type === "error"
                  ? "#991b1b"
                  : toast.type === "warning"
                  ? "#92400e"
                  : toast.type === "success"
                  ? "#166534"
                  : "var(--brand-900)",
              display: "flex",
              alignItems: "flex-start",
              gap: "var(--sp-3)",
              animation: "tabFadeIn 0.3s cubic-bezier(0,0,0.2,1)",
              fontFamily: "var(--font-sans)",
            }}
          >
            <span style={{ fontSize: "1.2rem", flexShrink: 0, marginTop: -1 }}>
              {toast.type === "error"
                ? "⚠️"
                : toast.type === "warning"
                ? "⚡"
                : toast.type === "success"
                ? "✅"
                : "💡"}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              {toast.title && (
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: "var(--text-sm)",
                    marginBottom: 2,
                  }}
                >
                  {toast.title}
                </div>
              )}
              <div
                style={{
                  fontSize: "var(--text-xs)",
                  lineHeight: 1.5,
                  wordBreak: "break-word",
                }}
              >
                {toast.message}
              </div>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "2px 4px",
                color: "inherit",
                opacity: 0.6,
                fontSize: "var(--text-sm)",
                fontWeight: 700,
              }}
              aria-label="Close notification"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
