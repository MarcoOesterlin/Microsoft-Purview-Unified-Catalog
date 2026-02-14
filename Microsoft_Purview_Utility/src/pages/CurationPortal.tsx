import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { CurationAction, ActionStatus } from "@/components/catalog/CurationAction";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Plus, 
  RefreshCw, 
  Play, 
  FileCode,
  Sparkles,
  Database,
  Tag,
  Link2,
  Shield,
} from "lucide-react";

const curationActions = [
  {
    id: "fetch_all",
    name: "Fetch All Assets",
    description: "Scan and import all data assets from connected sources",
    script: "python scripts/fetch_assets.py --source=all --include-metadata",
    lastRun: "Today, 09:30 AM",
    category: "discovery",
  },
  {
    id: "fetch_snowflake",
    name: "Fetch Snowflake Assets",
    description: "Import tables and views from Snowflake data warehouse",
    script: "python scripts/fetch_snowflake.py --database=PROD_DW",
    lastRun: "Yesterday, 11:45 PM",
    category: "discovery",
  },
  {
    id: "fetch_databricks",
    name: "Fetch Databricks Assets",
    description: "Import notebooks and tables from Databricks workspace",
    script: "python scripts/fetch_databricks.py --workspace=production",
    lastRun: "2 days ago",
    category: "discovery",
  },
  {
    id: "auto_classify",
    name: "Auto-Classify Data",
    description: "Run ML classification on untagged assets",
    script: "python scripts/auto_classify.py --model=bert-classifier-v2",
    lastRun: "Yesterday, 03:00 PM",
    category: "classification",
  },
  {
    id: "detect_pii",
    name: "Detect PII Data",
    description: "Scan assets for personally identifiable information",
    script: "python scripts/detect_pii.py --sensitivity=high",
    lastRun: "3 days ago",
    category: "classification",
  },
  {
    id: "sync_lineage",
    name: "Sync Data Lineage",
    description: "Update lineage relationships across all assets",
    script: "python scripts/sync_lineage.py --depth=5 --include-transforms",
    lastRun: "1 day ago",
    category: "lineage",
  },
  {
    id: "validate_quality",
    name: "Run Quality Checks",
    description: "Execute data quality validation rules",
    script: "python scripts/quality_checks.py --profile=production",
    lastRun: "Today, 06:00 AM",
    category: "quality",
  },
  {
    id: "sync_glossary",
    name: "Sync Business Glossary",
    description: "Update glossary terms and link to assets",
    script: "python scripts/sync_glossary.py --source=confluence",
    lastRun: "5 days ago",
    category: "governance",
  },
];

const categories = [
  { value: "all", label: "All Categories", icon: FileCode },
  { value: "discovery", label: "Discovery", icon: Database },
  { value: "classification", label: "Classification", icon: Tag },
  { value: "lineage", label: "Lineage", icon: Link2 },
  { value: "quality", label: "Quality", icon: Sparkles },
  { value: "governance", label: "Governance", icon: Shield },
];

export default function CurationPortal() {
  const [actionStatuses, setActionStatuses] = useState<Record<string, ActionStatus>>({});
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [showNewAction, setShowNewAction] = useState(false);

  const handleRunAction = (actionId: string) => {
    setActionStatuses((prev) => ({ ...prev, [actionId]: "running" }));
    
    // Simulate script execution
    setTimeout(() => {
      setActionStatuses((prev) => ({
        ...prev,
        [actionId]: Math.random() > 0.2 ? "success" : "error",
      }));
    }, 3000 + Math.random() * 2000);
  };

  const handleRunAll = () => {
    const filtered = categoryFilter === "all" 
      ? curationActions 
      : curationActions.filter(a => a.category === categoryFilter);
    
    filtered.forEach((action, index) => {
      setTimeout(() => handleRunAction(action.id), index * 500);
    });
  };

  const filteredActions = categoryFilter === "all"
    ? curationActions
    : curationActions.filter((a) => a.category === categoryFilter);

  return (
    <AppLayout
      title="Curation Actions"
      subtitle="Run Python scripts to automate data curation and governance tasks"
    >
      {/* Controls */}
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              {categories.map((cat) => (
                <SelectItem key={cat.value} value={cat.value}>
                  <div className="flex items-center gap-2">
                    <cat.icon className="w-4 h-4" />
                    {cat.label}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh Status
          </Button>
          <Button 
            variant="outline" 
            className="gap-2"
            onClick={handleRunAll}
          >
            <Play className="w-4 h-4" />
            Run All
          </Button>
          <Button className="gap-2" onClick={() => setShowNewAction(true)}>
            <Plus className="w-4 h-4" />
            New Action
          </Button>
        </div>
      </div>

      {/* New Action Form */}
      {showNewAction && (
        <Card className="p-6 mb-6 animate-fade-in">
          <h3 className="font-semibold mb-4">Create New Curation Action</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Action Name</Label>
              <Input placeholder="e.g., Fetch Azure Assets" />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.slice(1).map((cat) => (
                    <SelectItem key={cat.value} value={cat.value}>
                      {cat.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-2 space-y-2">
              <Label>Description</Label>
              <Input placeholder="Brief description of what this action does" />
            </div>
            <div className="col-span-2 space-y-2">
              <Label>Python Script Command</Label>
              <Textarea 
                placeholder="python scripts/my_script.py --arg=value"
                className="font-mono text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowNewAction(false)}>
              Cancel
            </Button>
            <Button onClick={() => setShowNewAction(false)}>
              Create Action
            </Button>
          </div>
        </Card>
      )}

      {/* Actions Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredActions.map((action) => (
          <CurationAction
            key={action.id}
            name={action.name}
            description={action.description}
            script={action.script}
            status={actionStatuses[action.id] || "idle"}
            lastRun={action.lastRun}
            onRun={() => handleRunAction(action.id)}
          />
        ))}
      </div>
    </AppLayout>
  );
}
