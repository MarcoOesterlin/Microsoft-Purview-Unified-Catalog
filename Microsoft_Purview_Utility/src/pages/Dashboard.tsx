import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { StatCard } from "@/components/catalog/StatCard";
import { AssetCard } from "@/components/catalog/AssetCard";
import {
  Database,
  Package,
  Table,
  Users,
  ArrowRight,
  Search,
  Sparkles,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePurviewAssets, usePurviewStats, useRefreshPurviewData } from "@/hooks/usePurviewData";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useToast } from "@/hooks/use-toast";

export default function Dashboard() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const { data: assetsData, isLoading: assetsLoading, error: assetsError } = usePurviewAssets();
  const assets = assetsData?.assets;
  const { data: stats, isLoading: statsLoading, error: statsError } = usePurviewStats();
  const { mutate: refreshData, isPending: isRefreshing } = useRefreshPurviewData();
  const { toast } = useToast();
  const [recentAssetIds, setRecentAssetIds] = useState<string[]>([]);

  // Load recently clicked assets from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('recentAssets');
    if (stored) {
      try {
        setRecentAssetIds(JSON.parse(stored));
      } catch (e) {
        console.error('Failed to parse recent assets', e);
      }
    }
  }, []);

  // Get recent assets based on clicked history only (no fallback)
  const recentAssets = recentAssetIds.length > 0 && assets
    ? recentAssetIds
        .map(id => assets.find(a => a.id === id))
        .filter(Boolean)
        .slice(0, 4)
    : [];

  // Track asset clicks
  const handleAssetClick = (assetId: string) => {
    const stored = localStorage.getItem('recentAssets');
    let recent: string[] = [];
    
    if (stored) {
      try {
        recent = JSON.parse(stored);
      } catch (e) {
        console.error('Failed to parse recent assets', e);
      }
    }
    
    // Remove if already exists and add to front
    recent = [assetId, ...recent.filter(id => id !== assetId)].slice(0, 10);
    localStorage.setItem('recentAssets', JSON.stringify(recent));
    setRecentAssetIds(recent);
  };
  
  // Helper function to parse tags/classifications properly
  const parseArray = (data: any): string[] => {
    if (!data) return [];
    if (Array.isArray(data)) return data.filter(t => t && typeof t === 'string');
    if (typeof data === 'string') return [data];
    return [];
  };
  
  // Helper to determine asset type
  const getAssetType = (asset: any): string => {
    const assetType = asset.assetType || asset.entityType || '';
    const entityType = asset.entityType?.toLowerCase() || '';
    
    // Map file types to 'file'
    if (assetType.includes('File') || assetType === 'Azure Blob') {
      return 'file';
    }
    
    // Use entityType, fallback to 'table'
    return entityType || 'table';
  };
  
  const mapAssetToCard = (asset: any) => {
    return {
      id: asset.id,
      name: asset.name || 'Unknown',
      type: getAssetType(asset) as any,
      description: asset.userDescription || asset.description || 'No description available',
      owner: asset.owner,
      expert: asset.expert,
      tags: parseArray(asset.tag),
      classifications: parseArray(asset.classification),
      status: 'verified' as const,
      connection: asset.qualifiedName || 'N/A',
      lastUpdated: asset.updateTime ? new Date(asset.updateTime).toLocaleDateString() : 'N/A',
      collectionName: asset.collectionName,
    };
  };

  const handleRefresh = () => {
    toast({
      title: "Syncing data...",
      description: "Fetching latest data from Microsoft Purview",
    });
    refreshData(undefined, {
      onSuccess: () => {
        toast({
          title: "Sync complete",
          description: "Assets and data products have been updated",
        });
      },
      onError: (error) => {
        toast({
          title: "Sync failed",
          description: error.message || "Failed to refresh data from Purview",
          variant: "destructive",
        });
      },
    });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/assets?search=${encodeURIComponent(searchQuery)}`);
    } else {
      navigate('/assets');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch(e as any);
    }
  };

  // Show full-screen loading spinner when initially loading
  if (assetsLoading && !assets) {
    return <LoadingSpinner fullScreen message="Loading data from Microsoft Purview..." size="lg" />;
  }

  return (
    <AppLayout
      title="Microsoft Purview Unified Catalog Utility"
    >
      <div className="p-6 space-y-8">
        {(assetsError || statsError) && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load data from Purview API. Make sure the Flask backend is running on port 8000.
              Error: {(assetsError || statsError)?.message}
            </AlertDescription>
          </Alert>
        )}

        <section className="text-center py-8">
          <h1 className="text-2xl font-semibold text-foreground mb-2">
            Find the data you need
          </h1>
          <p className="text-muted-foreground mb-6">
            Search across all your data assets, products, and glossary terms
          </p>
          <div className="relative max-w-2xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search assets and data products"
              className="w-full pl-12 pr-4 py-3 rounded-lg border border-border bg-card focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-base"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
            />
            <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-7 gap-1.5 text-xs"
                onClick={handleSearch}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Search
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-7 gap-1.5 text-xs"
                onClick={handleRefresh}
                disabled={isRefreshing}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Assets"
            value={statsLoading ? "..." : stats?.totalAssets.toLocaleString() || "0"}
            changeType="positive"
            icon={Table}
            onClick={() => navigate('/assets?view=all')}
          />
          <StatCard
            title="Asset Types"
            value={statsLoading ? "..." : Object.keys(stats?.assetTypes || {}).length.toString()}
            changeType="neutral"
            icon={Package}
            onClick={() => navigate('/assets?view=types')}
          />
          <StatCard
            title="With Tags"
            value={statsLoading ? "..." : stats?.withTags.toLocaleString() || "0"}
            changeType="positive"
            icon={Database}
            onClick={() => navigate('/assets?view=tags')}
          />
          <StatCard
            title="Classified"
            value={statsLoading ? "..." : stats?.withClassification.toLocaleString() || "0"}
            changeType="positive"
            icon={Users}
            onClick={() => navigate('/assets?view=classified')}
          />
        </section>

        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">
              Recent Assets {assetsLoading && "(Loading...)"}
            </h2>
            <Button variant="ghost" size="sm" className="gap-1.5 text-sm text-primary" asChild>
              <Link to="/assets">
                View All <ArrowRight className="w-4 h-4" />
              </Link>
            </Button>
          </div>
          <div className="pl-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {assetsLoading ? (
              <div className="col-span-4 flex justify-center py-12">
                <LoadingSpinner message="Loading recent assets..." />
              </div>
            ) : recentAssets.length === 0 ? (
              <div className="col-span-4 text-center py-8 text-muted-foreground">
                No recent assets yet. Click on assets in the Browse page to see them here.
              </div>
            ) : (
              recentAssets.map((asset, index) => (
                <AssetCard 
                  key={asset.id || asset.name || index} 
                  {...mapAssetToCard(asset)} 
                  onClick={() => handleAssetClick(asset.id)}
                />
              ))
            )}
            </div>
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
