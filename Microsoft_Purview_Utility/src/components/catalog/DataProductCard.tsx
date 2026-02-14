import { Package, Users, Layers, CheckCircle, MoreHorizontal, Clock, Archive, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DataProductCardProps {
  product: any;
  onClick?: () => void;
}

const statusConfig = {
  published: { icon: CheckCircle, label: "Published", color: "text-green-500" },
  active: { icon: CheckCircle, label: "Active", color: "text-green-500" },
  draft: { icon: Clock, label: "Draft", color: "text-yellow-500" },
  archived: { icon: Archive, label: "Archived", color: "text-gray-500" },
};

export function DataProductCard({ product, onClick }: DataProductCardProps) {
  const status = product.status?.toLowerCase() || "draft";
  const StatusIcon = statusConfig[status as keyof typeof statusConfig]?.icon || Clock;
  const statusLabel = statusConfig[status as keyof typeof statusConfig]?.label || "Unknown";
  const statusColor = statusConfig[status as keyof typeof statusConfig]?.color || "text-gray-500";

  return (
    <div
      onClick={onClick}
      className="bg-card border border-border rounded-lg p-4 card-hover cursor-pointer group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="p-2 rounded-lg bg-muted shrink-0">
            <Package className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-foreground truncate text-sm">
                {product.name || 'Unnamed Product'}
              </h3>
              {product.endorsed && (
                <Badge variant="secondary" className="text-[10px] font-normal px-1.5 py-0.5">
                  Endorsed
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <StatusIcon className={cn("w-3 h-3", statusColor)} />
              <span className="text-xs text-muted-foreground">{statusLabel}</span>
              {product.domain && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-xs text-primary truncate">{product.domain}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <MoreHorizontal className="w-4 h-4" />
        </Button>
      </div>

      {(product.description || product.businessUse) && (
        <p className="text-xs text-muted-foreground mt-3 line-clamp-2">
          {product.businessUse || product.description || 'No description available'}
        </p>
      )}

      {product.additionalProperties?.assetCount !== undefined && (
        <div className="flex items-center gap-1 mt-3">
          <Badge variant="outline" className="text-[10px] font-normal">
            {product.additionalProperties.assetCount} {product.additionalProperties.assetCount === 1 ? 'Asset' : 'Assets'}
          </Badge>
          {product.updateFrequency && (
            <Badge variant="outline" className="text-[10px] font-normal">
              {product.updateFrequency}
            </Badge>
          )}
        </div>
      )}

      <div className="flex items-center justify-between gap-2 mt-3 pt-3 border-t border-border">
        <span className="text-[10px] text-muted-foreground">
          {product.type || 'Data Product'}
        </span>
        {product.id && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 gap-1 text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => {
              e.stopPropagation();
              // Could open detail view or external link
            }}
          >
            <ExternalLink className="w-3 h-3" />
            View
          </Button>
        )}
      </div>
    </div>
  );
}
