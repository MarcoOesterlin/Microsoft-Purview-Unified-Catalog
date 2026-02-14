import { Bell, Settings, ChevronRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { useRefreshPurviewData } from "@/hooks/usePurviewData";
import { useToast } from "@/hooks/use-toast";

interface HeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: { label: string; href?: string }[];
  actions?: React.ReactNode;
}

export function Header({ title, subtitle, breadcrumbs, actions }: HeaderProps) {
  const { mutate: refreshData, isPending: isRefreshing } = useRefreshPurviewData();
  const { toast } = useToast();

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

  return (
    <header className="h-14 border-b border-border bg-card px-6 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {/* Breadcrumbs or Title */}
        {breadcrumbs && breadcrumbs.length > 0 ? (
          <nav className="flex items-center gap-1.5 text-sm">
            {breadcrumbs.map((crumb, index) => (
              <div key={index} className="flex items-center gap-1.5">
                {index > 0 && (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
                {crumb.href ? (
                  <a
                    href={crumb.href}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {crumb.label}
                  </a>
                ) : (
                  <span className={cn(
                    index === breadcrumbs.length - 1 
                      ? "font-semibold text-foreground" 
                      : "text-muted-foreground"
                  )}>
                    {crumb.label}
                  </span>
                )}
              </div>
            ))}
          </nav>
        ) : (
          <div>
            <h1 className="text-base font-semibold text-foreground">{title}</h1>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Global Sync Button */}
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Syncing...' : 'Sync'}
        </Button>

        {actions}
      </div>
    </header>
  );
}
