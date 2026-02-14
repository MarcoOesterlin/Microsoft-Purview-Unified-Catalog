import { AppLayout } from "@/components/layout/AppLayout";
import { Badge } from "@/components/ui/badge";
import { Package } from "lucide-react";
import { usePurviewDataProducts } from "@/hooks/usePurviewData";
import { DataProductCard } from "@/components/catalog/DataProductCard";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

export default function DataProducts() {
  const { data: products, isLoading, error } = usePurviewDataProducts();

  // Show full-screen loading spinner when initially loading
  if (isLoading && !products) {
    return <LoadingSpinner fullScreen message="Loading data products from Microsoft Purview..." size="lg" />;
  }

  return (
    <AppLayout
      title="Data Products"
      subtitle="Discover and consume curated data products"
    >
      <div className="space-y-6">
        {/* Header Info */}
        <div className="pl-4">
          {products && (
            <span className="text-sm text-muted-foreground">
              {products.length} {products.length === 1 ? 'product' : 'products'} found
            </span>
          )}
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-16">
            <LoadingSpinner message="Loading data products..." size="lg" />
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-16 text-destructive">
            Error loading data products: {error.message}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && (!products || products.length === 0) && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Package className="w-12 h-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium text-foreground">No Data Products Found</h3>
            <p className="text-muted-foreground mt-2 max-w-md">
              Data Products will appear here once they are created in your Purview catalog.
            </p>
          </div>
        )}

        {/* Data Products Grid */}
        {!isLoading && !error && products && products.length > 0 && (
          <div className="pl-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {products.map((product, index) => (
                <DataProductCard key={product.id || index} product={product} />
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
