import { Component, ErrorInfo, ReactNode } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SelectedAssetsProvider } from "./contexts/SelectedAssetsContext";
import { SelectedAssetsPanel } from "./components/catalog/SelectedAssetsPanel";
import Dashboard from "./pages/Dashboard";
import BrowseAssets from "./pages/BrowseAssets";
import BrowseByAssetType from "./pages/BrowseByAssetType";
import DataProducts from "./pages/DataProducts";
import DataSources from "./pages/DataSources";
import CurationPortal from "./pages/CurationPortal";
import Curate from "./pages/Curate";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Error Boundary to catch rendering errors
class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("React Error Boundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-background p-4">
          <div className="max-w-md text-center">
            <h1 className="text-2xl font-bold text-destructive mb-4">Something went wrong</h1>
            <p className="text-muted-foreground mb-4">{this.state.error?.message}</p>
            <pre className="text-xs bg-muted p-4 rounded overflow-auto text-left">
              {this.state.error?.stack}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const App = () => (
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <SelectedAssetsProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <SelectedAssetsPanel />
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/assets" element={<BrowseAssets />} />
              <Route path="/assets/by-type" element={<BrowseByAssetType />} />
              <Route path="/products" element={<DataProducts />} />
              <Route path="/sources" element={<DataSources />} />
              <Route path="/curation" element={<CurationPortal />} />
              <Route path="/curate" element={<Curate />} />
              {/* Placeholder routes */}
              <Route path="/governance" element={<Dashboard />} />
              <Route path="/owners" element={<Dashboard />} />
              <Route path="/docs" element={<Dashboard />} />
              <Route path="/settings" element={<Dashboard />} />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </SelectedAssetsProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

export default App;
