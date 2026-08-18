"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[PrepAI Global ErrorBoundary Caught]:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "60vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "var(--sp-8) var(--sp-6)",
            textAlign: "center",
            fontFamily: "var(--font-sans)",
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: 520,
              padding: "var(--sp-8)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "var(--sp-4)",
            }}
          >
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: "var(--r-2xl)",
                background: "var(--danger-bg)",
                color: "var(--danger-text)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "2rem",
              }}
            >
              ⚠️
            </div>

            <h2 style={{ fontSize: "var(--text-xl)", fontWeight: 800, color: "var(--gray-900)" }}>
              Something Went Wrong
            </h2>

            <p style={{ fontSize: "var(--text-sm)", color: "var(--gray-600)", lineHeight: 1.6 }}>
              {this.state.error?.message || "An unexpected error occurred in the application."}
            </p>

            <div style={{ display: "flex", gap: "var(--sp-3)", marginTop: "var(--sp-2)" }}>
              <button className="btn btn-secondary" onClick={this.handleReset}>
                Try Again
              </button>
              <button
                className="btn btn-primary"
                onClick={() => window.location.reload()}
              >
                Reload App
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
