import { Play, Loader2, CheckCircle, XCircle, Clock, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type ActionStatus = "idle" | "running" | "success" | "error";

interface CurationActionProps {
  name: string;
  description: string;
  script: string;
  status?: ActionStatus;
  lastRun?: string;
  onRun?: () => void;
}

export function CurationAction({
  name,
  description,
  script,
  status = "idle",
  lastRun,
  onRun,
}: CurationActionProps) {
  const statusConfig = {
    idle: { icon: Clock, color: "text-muted-foreground", bg: "bg-muted" },
    running: { icon: Loader2, color: "text-primary", bg: "bg-primary/10" },
    success: { icon: CheckCircle, color: "text-emerald-600", bg: "bg-emerald-100" },
    error: { icon: XCircle, color: "text-red-600", bg: "bg-red-100" },
  };

  const config = statusConfig[status] || statusConfig.idle; // Fallback to idle if status not found
  const StatusIcon = config.icon;

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={cn("p-2 rounded-lg", config.bg)}>
            <Terminal className={cn("w-5 h-5", config.color)} />
          </div>
          <div>
            <h3 className="font-medium text-foreground">{name}</h3>
            <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
          </div>
        </div>
        <Button
          onClick={onRun}
          disabled={status === "running"}
          className="gap-2"
          size="sm"
        >
          {status === "running" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {status === "running" ? "Running..." : "Run Script"}
        </Button>
      </div>

      <div className="mt-4 p-3 bg-muted/50 rounded-lg font-mono text-xs text-muted-foreground">
        <code>{script}</code>
      </div>

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-border">
        <div className="flex items-center gap-2">
          <StatusIcon
            className={cn(
              "w-4 h-4",
              config.color,
              status === "running" && "animate-spin"
            )}
          />
          <span className="text-sm text-muted-foreground capitalize">{status}</span>
        </div>
        {lastRun && (
          <span className="text-xs text-muted-foreground">Last run: {lastRun}</span>
        )}
      </div>
    </div>
  );
}
