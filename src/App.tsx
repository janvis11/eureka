import { lazy, Suspense } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import MainLayout from './layouts/MainLayout';

// Lazy load pages for better performance
const LandingPage = lazy(() => import('./pages/LandingPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraphPage'));
const DiscoveryPage = lazy(() => import('./pages/DiscoveryPage'));
const HypothesisPage = lazy(() => import('./pages/HypothesisPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

const LoadingFallback = () => (
  <div className="min-h-screen bg-black text-white flex items-center justify-center">
    <div className="text-center space-y-4">
      <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto"></div>
      <p className="text-gray-400">Loading...</p>
    </div>
  </div>
);

const App = () => (
  <ErrorBoundary>
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route
            path="/"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <LandingPage />
              </Suspense>
            }
          />
          <Route
            path="/chat"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <ChatPage />
              </Suspense>
            }
          />
          <Route
            path="/knowledge-graph"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <KnowledgeGraphPage />
              </Suspense>
            }
          />
          <Route
            path="/discovery"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <DiscoveryPage />
              </Suspense>
            }
          />
          <Route
            path="/hypothesis"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <HypothesisPage />
              </Suspense>
            }
          />
          <Route
            path="*"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <NotFoundPage />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  </ErrorBoundary>
);

export default App;

