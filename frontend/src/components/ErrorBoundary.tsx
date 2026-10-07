import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error) {
    console.error(error);
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="mx-auto max-w-lg px-6 py-24 text-center">
          <h1 className="text-2xl font-semibold">This page ran into a problem.</h1>
          <p className="mt-3 text-sm text-stone-600">Refresh the page and try again.</p>
        </div>
      );
    }
    return this.props.children;
  }
}
