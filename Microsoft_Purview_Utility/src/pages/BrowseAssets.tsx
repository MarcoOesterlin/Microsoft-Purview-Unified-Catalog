import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { AssetCard, AssetType } from "@/components/catalog/AssetCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Filter,
  LayoutGrid,
  List,
  SlidersHorizontal,
  Download,
  FolderTree,
  AlertTriangle,
} from "lucide-react";
import { usePurviewAssets } from "@/hooks/usePurviewData";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

export default function BrowseAssets() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { data: assetsData, isLoading, error } = usePurviewAssets();
  const assets = assetsData?.assets;
  const unmappedCollections = assetsData?.unmappedCollections || [];
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [collectionFilter, setCollectionFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [containerFilter, setContainerFilter] = useState<string | null>(null);
  const [allCollections, setAllCollections] = useState<Array<{id: string, name: string}>>([]);

  const view = searchParams.get('view');
  const searchQuery = searchParams.get('search');

  // Fetch all collections from the API
  useEffect(() => {
    fetch('http://localhost:8000/api/collections')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setAllCollections(data.data);
        }
      })
      .catch(err => console.error('Error fetching collections:', err));
  }, []);

  // Show full-screen loading spinner when initially loading
  if (isLoading && !assets) {
    return <LoadingSpinner fullScreen message="Loading assets from Microsoft Purview..." size="lg" />;
  }

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
  
  const allAssets = (assets || []).map((asset: any) => {
    return {
      id: asset.id,
      name: asset.name || 'Unknown',
      type: getAssetType(asset) as any,
      assetType: asset.assetType || asset.entityType || 'Unknown', // Preserve original assetType
      description: asset.userDescription || asset.description || 'No description available',
      owner: asset.owner,
      expert: asset.expert,
      tags: parseArray(asset.tag),
      classifications: parseArray(asset.classification),
      status: 'verified' as const,
      connection: asset.qualifiedName || 'N/A',
      lastUpdated: asset.updateTime ? new Date(asset.updateTime).toLocaleDateString() : 'N/A',      collectionName: asset.collectionName,    };
  });

  // Apply view-based filtering
  let viewFilteredAssets = allAssets;
  let viewTitle = "Browse Assets";
  
  if (view === 'all') {
    viewTitle = "All Assets";
  } else if (view === 'types') {
    viewTitle = "Assets by Type";
  } else if (view === 'tags') {
    viewTitle = "Assets with Tags";
    viewFilteredAssets = allAssets.filter(asset => asset.tags.length > 0);
  } else if (view === 'classified') {
    viewTitle = "Classified Assets";
    viewFilteredAssets = allAssets.filter(asset => 
      asset.classifications && asset.classifications.length > 0
    );
  } else if (searchQuery) {
    viewTitle = `Search Results: "${searchQuery}"`;
    viewFilteredAssets = allAssets.filter(asset => 
      asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      asset.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }

  // Get unique asset types from the data dynamically
  const uniqueAssetTypes = Array.from(
    new Set(allAssets.map(asset => asset.assetType).filter(Boolean))
  ).sort();

  const assetTypeOptions = [
    { value: "all", label: "All Types" },
    ...uniqueAssetTypes.map(type => ({
      value: type,
      label: type
    }))
  ];

  // Get unique collection names from the data dynamically
  const uniqueCollections = Array.from(
    new Set(allCollections.map(c => c.name).filter(Boolean))
  ).sort();

  const collectionOptions = [
    { value: "all", label: "All Collections" },
    ...uniqueCollections.map(collection => ({
      value: collection,
      label: collection
    }))
  ];

  const filteredAssets = viewFilteredAssets.filter((asset) => {
    if (typeFilter !== "all" && asset.assetType !== typeFilter) return false;
    if (collectionFilter !== "all" && asset.collectionName !== collectionFilter) return false;
    if (statusFilter !== "all" && asset.status !== statusFilter) return false;
    // Filter by container - show assets that start with the container URL
    if (containerFilter && !asset.connection.startsWith(containerFilter)) return false;
    return true;
  });

  // Track asset clicks and handle container navigation
  const handleAssetClick = (asset: any) => {
    // If clicking on a container, filter to show its contents
    if (asset.assetType === 'Azure Blob Container') {
      setContainerFilter(asset.connection);
      return;
    }
    
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
    recent = [asset.id, ...recent.filter(id => id !== asset.id)].slice(0, 10);
    localStorage.setItem('recentAssets', JSON.stringify(recent));
  };

  return (
    <AppLayout
      title={viewTitle}
      subtitle={
        view === 'tags' 
          ? "Assets organized by their tags"
          : view === 'classified'
          ? "Assets with classifications applied"
          : view === 'types'
          ? "Assets grouped by type"
          : "Explore and discover data assets across your organization"
      }
    >
      {/* Filters Bar */}
      <div className="flex items-center justify-center gap-4 mb-6 mt-6 px-8">
        <div className="flex items-center gap-3 w-full max-w-7xl bg-card border rounded-lg shadow-sm p-4">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => navigate('/assets/by-type')}
          >
            <FolderTree className="w-4 h-4" />
            By Type
          </Button>
          
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Asset Type" />
            </SelectTrigger>
            <SelectContent>
              {assetTypeOptions.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={collectionFilter} onValueChange={setCollectionFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Collection" />
            </SelectTrigger>
            <SelectContent>
              {collectionOptions.map((collection) => (
                <SelectItem key={collection.value} value={collection.value}>
                  {collection.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="verified">Verified</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
            </SelectContent>
          </Select>

          {(typeFilter !== "all" || collectionFilter !== "all" || statusFilter !== "all" || containerFilter) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setTypeFilter("all");
                setCollectionFilter("all");
                setStatusFilter("all");
                setContainerFilter(null);
              }}
            >
              Clear Filters
            </Button>
          )}
          
          {containerFilter && (
            <Badge variant="default" className="font-normal">
              Showing contents of: {containerFilter.split('/').pop()}
            </Badge>
          )}

          <div className="flex items-center gap-2 border-l pl-3 ml-2">
            <Badge variant="secondary" className="font-normal">
              {filteredAssets.length} assets
            </Badge>

            <div className="flex items-center border border-border rounded-lg p-1">
            <Button
              variant={viewMode === "grid" ? "secondary" : "ghost"}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setViewMode("grid")}
            >
              <LayoutGrid className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === "list" ? "secondary" : "ghost"}
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => setViewMode("list")}
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
        </div>
      </div>

      {/* Assets Grid */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner message="Loading assets..." size="lg" />
        </div>
      ) : (
        <div
          className="pl-4"
        >
          <div
            className={
              viewMode === "grid"
                ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                : "flex flex-col gap-3"
            }
          >
            {filteredAssets.map((asset, index) => (
            <AssetCard 
              key={asset.id || asset.name || index} 
              {...asset} 
              onClick={() => handleAssetClick(asset)}
            />
          ))}
          </div>
        </div>
      )}

      {filteredAssets.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Filter className="w-12 h-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium text-foreground">No assets found</h3>
          <p className="text-muted-foreground mt-1">
            Try adjusting your filters or search criteria
          </p>
        </div>
      )}
    </AppLayout>
  );
}
