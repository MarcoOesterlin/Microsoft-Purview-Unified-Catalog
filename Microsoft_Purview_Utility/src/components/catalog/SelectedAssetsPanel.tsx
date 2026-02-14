import { X, ChevronRight, ChevronLeft, Trash2, Copy, CheckSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useSelectedAssets } from '@/contexts/SelectedAssetsContext';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { getClassificationDisplayName } from '@/lib/classificationMapping';

export function SelectedAssetsPanel() {
  const { selectedAssets, removeAsset, clearAll } = useSelectedAssets();
  const [isHovered, setIsHovered] = useState(false);
  const { toast } = useToast();
  const [assetClassifications, setAssetClassifications] = useState<{ [guid: string]: string[] }>({});
  const [isLoadingClassifications, setIsLoadingClassifications] = useState(false);

  // Fetch classifications for all selected assets
  useEffect(() => {
    if (selectedAssets.length === 0) {
      setAssetClassifications({});
      return;
    }

    const fetchClassifications = async () => {
      setIsLoadingClassifications(true);
      try {
        const response = await fetch('http://localhost:8000/api/curate/get-classifications', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            guids: selectedAssets.map(a => a.id),
          }),
        });

        const data = await response.json();
        console.log('API Response:', { success: data.success, count: Object.keys(data.classifications || {}).length });

        if (response.ok && data.success) {
          setAssetClassifications(data.classifications || {});
        } else {
          console.error('Failed to fetch classifications:', data.error);
        }
      } catch (error) {
        console.error('Error fetching classifications:', error);
      } finally {
        setIsLoadingClassifications(false);
      }
    };

    fetchClassifications();
  }, [selectedAssets]);

  const copyAllGuids = () => {
    const guids = selectedAssets.map(a => a.id).join('\n');
    navigator.clipboard.writeText(guids);
    toast({
      title: "GUIDs Copied",
      description: `${selectedAssets.length} asset GUIDs copied to clipboard`,
    });
  };

  if (selectedAssets.length === 0) return null;

  return (
    <div
      className={cn(
        "fixed bottom-6 bg-gradient-to-br from-primary/10 to-primary/5 backdrop-blur-sm border-2 border-primary/30 shadow-2xl z-40 transition-all duration-300 flex flex-col rounded-xl hover:shadow-primary/20",
        isHovered ? "right-6 w-80 top-20" : "right-6 w-20 h-40"
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Collapsed State - Sleek vertical bar */}
      {!isHovered && (
        <div className="flex flex-col items-center justify-center h-full gap-4 py-6">
          <div className="relative">
            <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center shadow-lg ring-2 ring-primary/40 animate-pulse">
              <CheckSquare className="w-7 h-7 text-primary" />
            </div>
            <div className="absolute -top-1 -right-1 w-7 h-7 rounded-full bg-primary flex items-center justify-center shadow-md">
              <span className="text-xs font-bold text-primary-foreground">
                {selectedAssets.length}
              </span>
            </div>
          </div>
          <div className="writing-mode-vertical text-xs font-semibold text-primary tracking-widest">
            SELECTED
          </div>
        </div>
      )}

      {/* Expanded State - Shows on hover */}
      {isHovered && (
        <>
          {/* Header */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-sm">Selected Assets</h3>
                <Badge variant="secondary" className="text-xs">
                  {selectedAssets.length}
                </Badge>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={copyAllGuids}
                  title="Copy all GUIDs"
                >
                  <Copy className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={clearAll}
                  title="Clear all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Asset GUIDs for API operations
            </p>
          </div>

          {/* Asset List */}
          <div className="flex-1 overflow-y-auto p-2">
            <div className="space-y-1">
              {selectedAssets.map((asset) => {
                const classifications = assetClassifications[asset.id] || [];
                if (selectedAssets.length === 1) {
                  console.log('Asset ID:', asset.id, '| Classifications:', classifications, '| Available keys:', Object.keys(assetClassifications));
                }
                return (
                  <div
                    key={asset.id}
                    className="group bg-muted/50 rounded-md p-2 hover:bg-muted transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate">{asset.name}</p>
                        <p className="text-[10px] text-muted-foreground">{asset.type}</p>
                        <p className="text-[9px] text-muted-foreground/70 font-mono truncate" title={asset.id}>
                          GUID: {asset.id.slice(0, 8)}...
                        </p>
                        {/* Display Classifications */}
                        {/* Debug: loading={isLoadingClassifications.toString()}, count={classifications.length} */}
                        {isLoadingClassifications ? (
                          <div className="mt-1">
                            <Badge variant="outline" className="text-[9px] px-1 py-0 bg-blue-50">
                            </Badge>
                          </div>
                        ) : classifications.length > 0 ? (
                          <div className="mt-1 flex flex-wrap gap-0.5">
                            <span className="text-[9px] text-muted-foreground mr-1">Current:</span>
                            {classifications.slice(0, 2).map((cls, idx) => (
                              <Badge key={idx} variant="outline" className="text-[9px] px-1 py-0 bg-purple-50" title={cls}>
                                {getClassificationDisplayName(cls)}
                              </Badge>
                            ))}
                            {classifications.length > 2 && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0">
                                +{classifications.length - 2}
                              </Badge>
                            )}
                          </div>
                        ) : (
                          <div className="mt-1">
                            <Badge variant="outline" className="text-[9px] px-1 py-0 bg-gray-50 text-gray-500">
                              No classifications
                            </Badge>
                          </div>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => removeAsset(asset.id)}
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer Info */}
          <div className="p-3 border-t border-border">
            <p className="text-[10px] text-muted-foreground">
              Selected assets will be used for curation activities
            </p>
          </div>
        </>
      )}
    </div>
  );
}
