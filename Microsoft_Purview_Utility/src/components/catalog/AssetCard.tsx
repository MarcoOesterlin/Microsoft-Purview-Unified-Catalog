import { LucideIcon, Database, Table, Columns, Package, FileText, Tag, AlertTriangle, MoreHorizontal, CheckCircle2, File } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useSelectedAssets } from "@/contexts/SelectedAssetsContext";
import { getClassificationDisplayName } from "@/lib/classificationMapping";

export type AssetType = "database" | "table" | "column" | "dataset" | "product" | "glossary" | "view" | "model" | "file";

interface AssetCardProps {
  id?: string;
  name: string;
  type: AssetType;
  assetType?: string;
  description?: string;
  owner?: string;
  expert?: string;
  tags?: string[];
  classifications?: string[];
  status?: "verified" | "pending" | "draft";
  connection?: string;
  lastUpdated?: string;
  collectionName?: string;
  onClick?: () => void;
}

const typeConfig: Record<AssetType, { icon: LucideIcon; label: string }> = {
  database: { icon: Database, label: "Database" },
  table: { icon: Table, label: "Table" },
  column: { icon: Columns, label: "Column" },
  dataset: { icon: FileText, label: "Dataset" },
  product: { icon: Package, label: "Product" },
  glossary: { icon: Tag, label: "Term" },
  view: { icon: Table, label: "View" },
  model: { icon: Database, label: "Model" },
  file: { icon: File, label: "File" },
};

export function AssetCard({
  id,
  name,
  type,
  assetType,
  description,
  owner,
  expert,
  tags = [],
  classifications = [],
  status = "draft",
  connection,
  lastUpdated,
  collectionName,
  onClick,
}: AssetCardProps) {
  const config = typeConfig[type] || typeConfig.table; // Fallback to table if type not found
  const Icon = config.icon;
  const { addAsset, removeAsset, isSelected } = useSelectedAssets();
  const selected = id ? isSelected(id) : false;

  const handleSelect = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!id) return;
    
    if (selected) {
      removeAsset(id);
    } else {
      addAsset({ id, name, type, qualifiedName: connection });
    }
  };

  return (
    <div
      onClick={onClick}
      className={cn(
        "bg-card border rounded-lg p-4 card-hover cursor-pointer group relative transition-all",
        selected ? "border-primary ring-2 ring-primary/20" : "border-border"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="p-2 rounded-lg bg-muted shrink-0">
            <Icon className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-medium text-foreground truncate text-sm">{name}</h3>
            </div>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className="text-xs text-muted-foreground">{config.label}</span>
              {assetType && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                    {assetType}
                  </Badge>
                </>
              )}
            </div>
            {connection && (
              <div className="mt-1">
                <span className="text-[10px] text-primary truncate block font-mono">{connection}</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {id && (
            <Button
              variant={selected ? "default" : "outline"}
              size="icon"
              className={cn(
                "h-7 w-7 transition-all",
                selected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
              )}
              onClick={handleSelect}
              title={selected ? "Remove from selection" : "Add to selection"}
            >
              <CheckCircle2 className={cn("w-4 h-4", selected && "fill-current")} />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreHorizontal className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {description && (
        <p className="text-xs text-muted-foreground mt-3 line-clamp-2">
          {description}
        </p>
      )}

      {collectionName && (
        <div className="mt-3">
          <Badge variant="default" className="text-[10px] px-2 py-0.5">
            {collectionName}
          </Badge>
        </div>
      )}

      {(tags.length > 0 || classifications.length > 0) && (
        <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-border">
          {tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <Tag className="w-3 h-3 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground font-medium">Tags:</span>
              {tags.slice(0, 5).map((tag, index) => (
                <Badge key={`tag-${tag}-${index}`} variant="secondary" className="text-[10px] font-normal px-1.5 py-0.5">
                  {tag}
                </Badge>
              ))}
              {tags.length > 5 && (
                <span className="text-[10px] text-muted-foreground">+{tags.length - 5} more</span>
              )}
            </div>
          )}
          {classifications.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <AlertTriangle className="w-3 h-3 text-amber-600 flex-shrink-0" />
              <span className="text-[10px] text-muted-foreground font-medium flex-shrink-0">Classifications:</span>
              {classifications.slice(0, 3).map((classification, index) => (
                <Badge key={`class-${classification}-${index}`} variant="outline" className="text-[10px] font-normal px-1.5 py-0.5 border-amber-500 text-amber-700 truncate max-w-[200px]" title={classification}>
                  {getClassificationDisplayName(classification)}
                </Badge>
              ))}
              {classifications.length > 3 && (
                <span className="text-[10px] text-muted-foreground flex-shrink-0">+{classifications.length - 3} more</span>
              )}
            </div>
          )}
        </div>
      )}

      {(owner || expert || lastUpdated) && (
        <div className="flex flex-col gap-1 mt-3 pt-3 border-t border-border">
          <div className="flex items-center justify-between gap-2">
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              {owner && (
                <span className="text-[10px] text-muted-foreground truncate">
                  <span className="font-medium">Owner:</span> {owner}
                </span>
              )}
              {expert && (
                <span className="text-[10px] text-muted-foreground truncate">
                  <span className="font-medium">Expert:</span> {expert}
                </span>
              )}
            </div>
            {lastUpdated && (
              <span className="text-[10px] text-muted-foreground shrink-0">{lastUpdated}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
