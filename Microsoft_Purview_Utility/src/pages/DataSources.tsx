import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus } from "lucide-react";

// Data Sources will be configured separately from asset catalog

export default function DataSources() {
  return (
    <AppLayout
      title="Data Sources"
      subtitle="Manage connections to your data platforms"
    >
      <div className="flex items-center justify-between mb-6">
        <Input 
          placeholder="Search data sources..." 
          className="max-w-sm"
        />
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Add Data Source
        </Button>
      </div>

      <div className="flex flex-col items-center justify-center py-16 text-center">
        <h3 className="text-lg font-medium text-foreground">No Data Sources Configured</h3>
        <p className="text-muted-foreground mt-2 max-w-md">
          Connect your data sources to start cataloging assets. Add Snowflake, Databricks, Azure SQL, and more.
        </p>
        <Button className="gap-2 mt-6">
          <Plus className="w-4 h-4" />
          Add Your First Source
        </Button>
      </div>
    </AppLayout>
  );
}
