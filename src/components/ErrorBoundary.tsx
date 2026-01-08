import { Component, ErrorInfo, ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center px-6">
          <div className="max-w-md text-center space-y-6">
            <h1 className="text-4xl font-bold">System Error</h1>
            <p className="text-gray-400">
              Something went wrong. The error has been logged and we're working on a fix.
            </p>
            {this.state.error && (
              <details className="text-left bg-gray-900 p-4 rounded text-xs text-gray-400">
                <summary className="cursor-pointer mb-2">Error Details</summary>
                <pre className="whitespace-pre-wrap">{this.state.error.message}</pre>
              </details>
            )}
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-3 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition"
              >
                Reload Page
              </button>
              <Link
                to="/"
                className="px-6 py-3 border border-white text-white font-semibold rounded-full hover:bg-white hover:text-black transition"
              >
                Go Home
              </Link>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

