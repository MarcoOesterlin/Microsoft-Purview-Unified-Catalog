import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon: LucideIcon;
  onClick?: () => void;
}

export function StatCard({
  title,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  onClick,
}: StatCardProps) {
  const changeColors = {
    positive: "text-emerald-600",
    negative: "text-red-600",
    neutral: "text-muted-foreground",
  };

  return (
    <div 
      className={cn(
        "bg-card border border-border rounded-lg p-4",
        onClick && "cursor-pointer card-hover"
      )}
      onClick={onClick}
    >
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-muted">
          <Icon className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="flex-1">
          <p className="text-xs text-muted-foreground">{title}</p>
          <div className="flex items-baseline gap-2">
            <p className="text-xl font-semibold">{value}</p>
            {change && (
              <p className={cn("text-xs", changeColors[changeType])}>
                {change}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
