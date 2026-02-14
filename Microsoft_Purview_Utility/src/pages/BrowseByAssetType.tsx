import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { AssetCard } from "@/components/catalog/AssetCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { getClassificationDisplayName } from "@/lib/classificationMapping";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Search,
  Database,
  Table,
  Columns,
  FileText,
  Package,
  LayoutGrid,
  List,
  HardDrive,
  FolderOpen,
  Tag,
  Snowflake,
  User,
} from "lucide-react";
import { usePurviewAssets } from "@/hooks/usePurviewData";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";
import { useSelectedAssets } from "@/contexts/SelectedAssetsContext";

export default function BrowseByAssetType() {
  const { data: assetsData, isLoading } = usePurviewAssets();
  const assets = assetsData?.assets;
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const { addAsset, removeAsset, isSelected } = useSelectedAssets();

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

  // Helper function to parse contact information
  const parseContacts = (contact: any): { owner?: string; expert?: string } => {
    if (!contact) return {};
    if (Array.isArray(contact)) {
      const ownerContact = contact.find(c => c.contactType === 'Owner');
      const expertContact = contact.find(c => c.contactType === 'Expert');
      return {
        owner: ownerContact?.id,
        expert: expertContact?.id,
      };
    }
    if (typeof contact === 'string') return { owner: contact };
    return {};
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
      assetType: asset.assetType || asset.entityType || 'Unknown',
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
  });

  // Filter assets by search query
  const filteredAssets = allAssets.filter(asset => 
    asset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    asset.assetType.toLowerCase().includes(searchQuery.toLowerCase()) ||
    asset.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group assets by asset type
  const assetsByType = filteredAssets.reduce((acc, asset) => {
    const type = asset.assetType;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(asset);
    return acc;
  }, {} as Record<string, typeof allAssets>);

  // Sort types by count (descending)
  const sortedTypes = Object.entries(assetsByType).sort(
    ([, a], [, b]) => b.length - a.length
  );

  const toggleType = (type: string) => {
    setExpandedTypes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    setExpandedTypes(new Set(sortedTypes.map(([type]) => type)));
  };

  const collapseAll = () => {
    setExpandedTypes(new Set());
  };

  const toggleNode = (nodeId: string) => {
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  };

  // Build Azure Storage hierarchy
  const buildStorageHierarchy = (storageAssets: typeof allAssets) => {
    const accounts: any[] = [];
    const accountChildren: Record<string, any[]> = {};
    const blobStorageChildren: Record<string, any[]> = {};
    const containerChildren: Record<string, any[]> = {};

    // Organize by hierarchy level (4 levels: Account -> Blob Storage -> Container -> Files)
    storageAssets.forEach(asset => {
      if (asset.assetType === 'Azure Storage Account') {
        accounts.push(asset);
        accountChildren[asset.connection] = [];
      } else if (asset.assetType === 'Azure Blob Storage') {
        const accountUrl = asset.connection.replace('.blob.core.windows.net', '.core.windows.net');
        if (!accountChildren[accountUrl]) accountChildren[accountUrl] = [];
        accountChildren[accountUrl].push(asset);
        blobStorageChildren[asset.connection] = [];
      } else if (asset.assetType === 'Azure Blob Container') {
        const blobStorageUrl = asset.connection.substring(0, asset.connection.lastIndexOf('/'));
        if (!blobStorageChildren[blobStorageUrl]) blobStorageChildren[blobStorageUrl] = [];
        blobStorageChildren[blobStorageUrl].push(asset);
        containerChildren[asset.connection] = [];
      } else if (asset.assetType?.includes('File') || asset.assetType === 'Azure Blob') {
        // Level 4: Files (CSV File, JSON File, Azure Blob, etc.) are children of containers
        const containerUrl = asset.connection.substring(0, asset.connection.lastIndexOf('/'));
        if (!containerChildren[containerUrl]) containerChildren[containerUrl] = [];
        containerChildren[containerUrl].push(asset);
      }
    });

    return { accounts, accountChildren, blobStorageChildren, containerChildren };
  };

  // Render storage hierarchy node
  const renderStorageNode = (asset: any, children: any[], level: number, childrenMap: any) => {
    const hasChildren = children && children.length > 0;
    const isNodeExpanded = expandedNodes.has(asset.id);
    const selected = isSelected(asset.id);
    const isSelectable = !hasChildren; // Only leaf nodes are selectable
    
    const getIcon = () => {
      if (asset.assetType === 'Azure Storage Account') return HardDrive;
      if (asset.assetType === 'Azure Blob Storage') return Database;
      if (asset.assetType === 'Azure Blob Container') return FolderOpen;
      return FileText;
    };
    
    const Icon = getIcon();

    const handleSelect = (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!isSelectable) return;
      
      if (selected) {
        removeAsset(asset.id);
      } else {
        addAsset({ 
          id: asset.id, 
          name: asset.name, 
          type: asset.type, 
          qualifiedName: asset.connection 
        });
      }
    };

    return (
      <div key={asset.id} style={{ marginLeft: level * 16 }}>
        <div 
          className={cn(
            "flex items-start gap-3 py-3 px-3 hover:bg-muted/30 rounded-lg transition-all group border",
            isSelectable && "cursor-pointer",
            selected ? "bg-primary/5 border-primary" : "border-transparent"
          )}
        >
          {hasChildren ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0 mt-0.5"
              onClick={(e) => {
                e.stopPropagation();
                toggleNode(asset.id);
              }}
            >
              {isNodeExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </Button>
          ) : (
            <div className="w-6 shrink-0" />
          )}

          {isSelectable ? (
            <Checkbox
              checked={selected}
              onClick={handleSelect}
              className="shrink-0 mt-1"
            />
          ) : (
            <div className="w-4 shrink-0" />
          )}
          
          <div className="p-2 rounded-lg bg-muted shrink-0">
            <Icon className="w-4 h-4 text-muted-foreground" />
          </div>
          
          <div 
            className="flex-1 min-w-0" 
            onClick={isSelectable ? handleSelect : undefined}
          >
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className="text-sm font-semibold truncate">{asset.name}</span>
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                {asset.assetType}
              </Badge>
              {asset.collectionName && (
                <Badge variant="default" className="text-[10px] px-1.5 py-0">
                  {asset.collectionName}
                </Badge>
              )}
              {hasChildren && (
                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                  {children.length} {children.length === 1 ? 'child' : 'children'}
                </Badge>
              )}
            </div>
            
            {asset.description && (
              <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                {asset.description}
              </p>
            )}

            <div className="flex flex-col gap-1.5 text-xs">
              {(asset.owner || asset.expert) && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <User className="w-3 h-3" />
                  <span>
                    {asset.owner && `Owner: ${asset.owner}`}
                    {asset.owner && asset.expert && ' | '}
                    {asset.expert && `Expert: ${asset.expert}`}
                  </span>
                </div>
              )}

              {asset.tags && asset.tags.length > 0 && (
                <div className="flex items-center gap-2">
                  <Tag className="w-3 h-3 text-blue-500" />
                  <div className="flex items-center gap-1 flex-wrap">
                    {asset.tags.slice(0, 3).map((tag: string, idx: number) => (
                      <Badge key={idx} variant="outline" className="text-[10px] px-1.5 py-0 bg-blue-50">
                        {tag}
                      </Badge>
                    ))}
                    {asset.tags.length > 3 && (
                      <span className="text-[10px] text-muted-foreground">
                        +{asset.tags.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {asset.classifications && asset.classifications.length > 0 && (
                <div className="flex items-center gap-2">
                  <Snowflake className="w-3 h-3 text-purple-500" />
                  <div className="flex items-center gap-1 flex-wrap">
                    {asset.classifications.slice(0, 3).map((classification: string, idx: number) => (
                      <Badge key={idx} variant="outline" className="text-[10px] px-1.5 py-0 bg-purple-50" title={classification}>
                        {getClassificationDisplayName(classification)}
                      </Badge>
                    ))}
                    {asset.classifications.length > 3 && (
                      <span className="text-[10px] text-muted-foreground">
                        +{asset.classifications.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              <div className="text-[10px] text-muted-foreground truncate font-mono bg-muted/30 px-2 py-1 rounded">
                {asset.connection}
              </div>

              {asset.lastUpdated && (
                <div className="text-[10px] text-muted-foreground">
                  Last updated: {asset.lastUpdated}
                </div>
              )}
            </div>
          </div>
        </div>

        {isNodeExpanded && hasChildren && (
          <div className="mt-2 space-y-2">
            {children.map(child => {
              // Determine the correct children for this child node
              let childChildren: any[] = [];
              if (child.assetType === 'Azure Storage Account') {
                childChildren = childrenMap.accountChildren?.[child.connection] || [];
              } else if (child.assetType === 'Azure Blob Storage') {
                childChildren = childrenMap.blobStorageChildren?.[child.connection] || [];
              } else if (child.assetType === 'Azure Blob Container') {
                childChildren = childrenMap.containerChildren?.[child.connection] || [];
              }
              return renderStorageNode(child, childChildren, level + 1, childrenMap);
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <AppLayout
      title="Browse by Asset Type"
      subtitle="Explore assets organized by their type classification"
    >
      {/* Search and Controls Bar */}
      <div className="flex items-center justify-center gap-4 mb-6 mt-6 px-8">
        <div className="flex items-center gap-3 w-full max-w-7xl bg-card border rounded-lg shadow-sm p-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search assets or types..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button variant="outline" size="sm" onClick={expandAll}>
            Expand All
          </Button>
          <Button variant="outline" size="sm" onClick={collapseAll}>
            Collapse All
          </Button>

          <div className="flex items-center gap-2 border-l pl-3 ml-2">
            <Badge variant="secondary" className="font-normal">
              {sortedTypes.length} types • {filteredAssets.length} assets
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

      {/* Asset Type Groups */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner message="Loading assets..." size="lg" />
        </div>
      ) : sortedTypes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Search className="w-12 h-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium text-foreground">No assets found</h3>
          <p className="text-muted-foreground mt-1">
            Try adjusting your search criteria
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedTypes.map(([type, typeAssets]) => {
            const isExpanded = expandedTypes.has(type);
            const isStorageType = type.includes('Azure Storage') || type.includes('Azure Blob');
            
            // For storage types, build hierarchy
            if (isStorageType && type === 'Azure Storage Account') {
              const allStorageAssets = [
                ...assetsByType['Azure Storage Account'] || [],
                ...assetsByType['Azure Blob Storage'] || [],
                ...assetsByType['Azure Blob Container'] || [],
                ...assetsByType['Azure Blob'] || [],
                ...assetsByType['CSV File'] || [],
                ...assetsByType['JSON File'] || [],
                ...assetsByType['PARQUET File'] || [],
                ...assetsByType['TXT File'] || [],
                ...assetsByType['XML File'] || [],
                // Add any other file types that might exist
                ...Object.entries(assetsByType)
                  .filter(([t]) => t.includes('File') && !['CSV File', 'JSON File', 'PARQUET File', 'TXT File', 'XML File'].includes(t))
                  .flatMap(([, assets]) => assets)
              ];
              
              const { accounts, accountChildren, blobStorageChildren, containerChildren } = buildStorageHierarchy(allStorageAssets);
              
              return (
                <Collapsible
                  key="azure-storage-hierarchy"
                  open={isExpanded}
                  onOpenChange={() => toggleType(type)}
                >
                  <Card>
                    <CollapsibleTrigger asChild>
                      <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-primary/10">
                              <HardDrive className="w-5 h-5 text-primary" />
                            </div>
                            <div>
                              <CardTitle className="text-lg">Azure Storage Hierarchy</CardTitle>
                              <CardDescription>
                                {allStorageAssets.length} storage {allStorageAssets.length === 1 ? 'asset' : 'assets'}
                              </CardDescription>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="font-mono">
                              {allStorageAssets.length}
                            </Badge>
                            {isExpanded ? (
                              <ChevronUp className="w-5 h-5 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="w-5 h-5 text-muted-foreground" />
                            )}
                          </div>
                        </div>
                      </CardHeader>
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <CardContent className="pt-0">
                        {accounts.map(account => 
                          renderStorageNode(
                            account,
                            accountChildren[account.connection] || [],
                            0,
                            { accountChildren, blobStorageChildren, containerChildren }
                          )
                        )}
                      </CardContent>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              );
            }
            
            // Skip individual storage asset types as they're shown in hierarchy
            if (isStorageType) return null;
            
            return (
              <Collapsible
                key={type}
                open={isExpanded}
                onOpenChange={() => toggleType(type)}
              >
                <Card>
                  <CollapsibleTrigger asChild>
                    <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-primary/10">
                            <Database className="w-5 h-5 text-primary" />
                          </div>
                          <div>
                            <CardTitle className="text-lg">{type}</CardTitle>
                            <CardDescription>
                              {typeAssets.length} {typeAssets.length === 1 ? 'asset' : 'assets'}
                            </CardDescription>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="font-mono">
                            {typeAssets.length}
                          </Badge>
                          {isExpanded ? (
                            <ChevronUp className="w-5 h-5 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="w-5 h-5 text-muted-foreground" />
                          )}
                        </div>
                      </div>
                    </CardHeader>
                  </CollapsibleTrigger>

                  <CollapsibleContent>
                    <CardContent className="pt-0">
                      <div
                        className={cn(
                          viewMode === "grid"
                            ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                            : "flex flex-col gap-3"
                        )}
                      >
                        {typeAssets.map((asset, index) => (
                          <AssetCard
                            key={asset.id || `${type}-${index}`}
                            {...asset}
                          />
                        ))}
                      </div>
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </Collapsible>
            );
          })}
        </div>
      )}
    </AppLayout>
  );
}
