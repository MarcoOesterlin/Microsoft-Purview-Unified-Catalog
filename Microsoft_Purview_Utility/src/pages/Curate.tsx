import { useState, useEffect } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { useSelectedAssets } from "@/contexts/SelectedAssetsContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Tag, AlertCircle, CheckCircle2, X, Trash2, RefreshCw, User, UserCog, Users, Shield, Sparkles, GitBranch, ArrowRight, ChevronDown, Edit, Database, FileText, Check, Eye, EyeOff, BookOpen } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { getClassificationDisplayName } from "@/lib/classificationMapping";

interface EntraUser {
  id: string;
  displayName: string;
}

interface Classification {
  name: string;
  description: string;
  category: string;
}

interface SchemaColumn {
  guid: string;
  name: string;
  type: string;
  existing_classifications?: string[];
}

interface SchemaData {
  has_schema: boolean;
  classifications?: {
    [columnGuid: string]: {
      name: string;
      classifications: string[];
    };
  };
  asset_classifications?: string[];
  schema: SchemaColumn[];
}

interface AutoClassificationSuggestions {
  [entityGuid: string]: {
    has_schema: boolean;
    classifications?: {
      [columnGuid: string]: {
        name: string;
        classifications: string[];
      };
    };
  };
}

export default function Curate() {
  const { selectedAssets, addAsset, removeAsset, clearAll, getGuids } = useSelectedAssets();
  const { toast } = useToast();
  const [addTagInput, setAddTagInput] = useState("");
  const [removeTagInput, setRemoveTagInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<{ success: boolean; message: string } | null>(null);
  const [existingTags, setExistingTags] = useState<string[]>([]);
  const [isLoadingTags, setIsLoadingTags] = useState(false);

  // Helper function to extract container name from qualified name
  const extractContainerInfo = (qualifiedName: string) => {
    if (!qualifiedName) return null;
    
    // Extract lakehouse name
    const lakehouseMatch = qualifiedName.match(/\/lakehouses\/[^/]+/);
    if (lakehouseMatch) {
      // Get the lakehouse ID and try to find name from workspace info
      const lakehouseId = lakehouseMatch[0].split('/').pop();
      
      // If we have workspace info, look up the lakehouse name
      if (discoveredLineage?.workspace_info?.lakehouses) {
        const lakehouse = discoveredLineage.workspace_info.lakehouses.find(
          (lh: any) => lh.qualified_name.includes(lakehouseId || '')
        );
        if (lakehouse) {
          return { type: 'Lakehouse', name: lakehouse.name };
        }
      }
      return { type: 'Lakehouse', name: lakehouseId };
    }
    
    // Extract warehouse name
    const warehouseMatch = qualifiedName.match(/\/lakewarehouses\/[^/]+/);
    if (warehouseMatch) {
      const warehouseId = warehouseMatch[0].split('/').pop();
      
      if (discoveredLineage?.workspace_info?.warehouses) {
        const warehouse = discoveredLineage.workspace_info.warehouses.find(
          (wh: any) => wh.qualified_name.includes(warehouseId || '')
        );
        if (warehouse) {
          return { type: 'Warehouse', name: warehouse.name };
        }
      }
      return { type: 'Warehouse', name: warehouseId };
    }
    
    return null;
  };
  
  // Owner/Expert states
  const [users, setUsers] = useState<EntraUser[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [selectedOwner, setSelectedOwner] = useState<string>("");
  const [selectedExpert, setSelectedExpert] = useState<string>("");
  const [ownerNotes, setOwnerNotes] = useState("");
  const [expertNotes, setExpertNotes] = useState("");
  const [existingOwners, setExistingOwners] = useState<EntraUser[]>([]);
  const [existingExperts, setExistingExperts] = useState<EntraUser[]>([]);
  const [isLoadingContacts, setIsLoadingContacts] = useState(false);
  
  // Action states for merged tabs
  const [tagAction, setTagAction] = useState<'add' | 'remove'>('add');
  const [contactType, setContactType] = useState<'owner' | 'expert' | 'both'>('owner');
  const [contactAction, setContactAction] = useState<'add' | 'remove'>('add');
  
  // Classification states
  const [classifications, setClassifications] = useState<Classification[]>([]);
  const [isLoadingClassifications, setIsLoadingClassifications] = useState(false);
  const [selectedClassifications, setSelectedClassifications] = useState<string[]>([]);
  const [existingClassifications, setExistingClassifications] = useState<string[]>([]);
  const [isLoadingExistingClassifications, setIsLoadingExistingClassifications] = useState(false);
  const [classificationAction, setClassificationAction] = useState<'add' | 'remove'>('add');
  
  // Schema and column classification states
  const [schemaData, setSchemaData] = useState<{ [guid: string]: SchemaData }>({});
  const [isLoadingSchema, setIsLoadingSchema] = useState(false);
  const [columnClassifications, setColumnClassifications] = useState<{ [columnGuid: string]: string[] }>({});
  const [showSchemaView, setShowSchemaView] = useState(false);
  const [classificationSearchTerm, setClassificationSearchTerm] = useState("");
  const [isAutoClassifying, setIsAutoClassifying] = useState(false);
  const [autoClassificationSuggestions, setAutoClassificationSuggestions] = useState<AutoClassificationSuggestions>({});

  // Lineage states
  const [workspaces, setWorkspaces] = useState<Array<{ workspace_id: string; workspace_name: string; asset_count: number }>>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>("");
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(false);
  const [isDiscoveringLineage, setIsDiscoveringLineage] = useState(false);
  const [discoveredLineage, setDiscoveredLineage] = useState<any>(null);
  const [isCreatingLineage, setIsCreatingLineage] = useState(false);
  const [lineageMappings, setLineageMappings] = useState<Array<{ source_guid: string; target_guid: string; process_name: string; column_mappings?: any[] }>>([]);
  const [selectedMappingIndices, setSelectedMappingIndices] = useState<Set<number>>(new Set());
  const [editingMappingIndex, setEditingMappingIndex] = useState<number | null>(null);
  const [createdLineages, setCreatedLineages] = useState<Array<{ process_guid: string; process_name: string; source_name: string; target_name: string }>>([]);
  const [selectedLineageIndices, setSelectedLineageIndices] = useState<Set<number>>(new Set());
  
  // Description generation state
  const [selectedDescriptionAssets, setSelectedDescriptionAssets] = useState<Set<string>>(new Set());
  const [descriptionResults, setDescriptionResults] = useState<Array<{guid: string; name: string; description: string; asset_type: string}>>([]);
  const [isGeneratingDescription, setIsGeneratingDescription] = useState(false);
  
  // UI preferences
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [isApplyingDescriptions, setIsApplyingDescriptions] = useState(false);
  const [editingDescriptions, setEditingDescriptions] = useState<{[guid: string]: string}>({});
  const [originalHtmlDescriptions, setOriginalHtmlDescriptions] = useState<{[guid: string]: string}>({});
  const [activeTab, setActiveTab] = useState<string>('tags');

  // Orphaned assets state
  const [orphanedAssets, setOrphanedAssets] = useState<Array<{id: string; name: string; assetType: string; inactive_owner_ids: string[]; inactive_expert_ids: string[]; has_inactive_owner: boolean; has_inactive_expert: boolean}>>([]);
  const [isLoadingOrphanedAssets, setIsLoadingOrphanedAssets] = useState(false);

  // Business Glossary sync state
  const [glossaryPreview, setGlossaryPreview] = useState<any>(null);
  const [isLoadingGlossaryPreview, setIsLoadingGlossaryPreview] = useState(false);
  const [isSyncingGlossary, setIsSyncingGlossary] = useState(false);
  const [glossarySyncResult, setGlossarySyncResult] = useState<any>(null);

  // Fetch Entra ID users on mount
  useEffect(() => {
    fetchUsers();
    fetchAllClassifications();
  }, []);

  // Fetch existing tags and contacts when selected assets change
  useEffect(() => {
    if (selectedAssets.length > 0) {
      fetchExistingTags();
      fetchExistingContacts();
      fetchExistingClassifications();
    } else {
      setExistingTags([]);
      setExistingOwners([]);
      setExistingExperts([]);
      setExistingClassifications([]);
    }
  }, [selectedAssets]);

  const fetchUsers = async () => {
    setIsLoadingUsers(true);
    try {
      const response = await fetch("http://localhost:8000/api/users");
      const data = await response.json();

      if (response.ok && data.success) {
        setUsers(data.users || []);
      } else {
        console.error("Failed to fetch users:", data.error);
      }
    } catch (error) {
      console.error("Error fetching users:", error);
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const fetchOrphanedAssets = async () => {
    setIsLoadingOrphanedAssets(true);
    try {
      const response = await fetch("http://localhost:8000/api/orphaned-assets");
      const data = await response.json();

      if (response.ok && data.success) {
        setOrphanedAssets(data.orphaned_assets || []);
        toast({
          title: "Orphaned Assets Found",
          description: `Found ${data.total_count} asset(s) with inactive owners or experts`,
          duration: 5000,
        });
      } else {
        console.error("Failed to fetch orphaned assets:", data.error);
        toast({
          title: "Error",
          description: data.error || "Failed to fetch orphaned assets",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error fetching orphaned assets:", error);
      toast({
        title: "Error",
        description: "Failed to connect to server",
        variant: "destructive",
      });
    } finally {
      setIsLoadingOrphanedAssets(false);
    }
  };

  const fetchAllClassifications = async () => {
    setIsLoadingClassifications(true);
    try {
      const response = await fetch("http://localhost:8000/api/classifications");
      const data = await response.json();

      if (response.ok && data.success) {
        setClassifications(data.classifications || []);
      } else {
        console.error("Failed to fetch classifications:", data.error);
      }
    } catch (error) {
      console.error("Error fetching classifications:", error);
    } finally {
      setIsLoadingClassifications(false);
    }
  };

  const fetchSchema = async () => {
    if (selectedAssets.length === 0) return;
    
    setIsLoadingSchema(true);
    try {
      const response = await fetch("http://localhost:8000/api/curate/get-schema", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        const schemaData = data.schema_data || {};
        setSchemaData(schemaData);
        
        // Pre-populate existing classifications into columnClassifications state
        const existingColumnClassifications: { [columnGuid: string]: string[] } = {};
        Object.values(schemaData).forEach((assetData: any) => {
          if (assetData.schema && Array.isArray(assetData.schema)) {
            assetData.schema.forEach((column: any) => {
              console.log(`Column ${column.name}: existing_classifications =`, column.existing_classifications);
              if (column.existing_classifications && column.existing_classifications.length > 0) {
                existingColumnClassifications[column.guid] = column.existing_classifications;
              }
            });
          }
        });
        
        setColumnClassifications(existingColumnClassifications);
        console.log('Pre-populated column classifications:', existingColumnClassifications);
        setShowSchemaView(true);
      } else {
        throw new Error(data.error || "Failed to fetch schema");
      }
    } catch (error) {
      console.error("Error fetching schema:", error);
      toast({
        title: " Error Fetching Schema",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoadingSchema(false);
    }
  };

  const applyColumnClassifications = async () => {
    if (Object.keys(columnClassifications).length === 0) {
      toast({
        title: "No Classifications Selected",
        description: "Please select classifications for columns",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch("http://localhost:8000/api/curate/classify-columns", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          column_classifications: columnClassifications,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Classifications Applied",
          description: `Applied classifications to ${Object.keys(columnClassifications).length} column(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setColumnClassifications({});
        setShowSchemaView(false);
        fetchExistingClassifications();
      } else {
        throw new Error(data.error || "Failed to apply classifications");
      }
    } catch (error) {
      toast({
        title: " Error Applying Classifications",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const fetchExistingClassifications = async () => {
    setIsLoadingExistingClassifications(true);
    try {
      const response = await fetch("http://localhost:8000/api/curate/get-classifications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Backend returns {guid: [classifications]} object, need to flatten to array
        const classificationsObj = data.classifications || {};
        const allClassifications = new Set<string>();
        
        // Collect all unique classifications from all assets
        Object.values(classificationsObj).forEach((classArray: any) => {
          if (Array.isArray(classArray)) {
            classArray.forEach((cls: string) => allClassifications.add(cls));
          }
        });
        
        setExistingClassifications(Array.from(allClassifications));
        console.log('Fetched classifications:', Array.from(allClassifications));
      } else {
        console.error("Failed to fetch classifications:", data.error);
      }
    } catch (error) {
      console.error("Error fetching classifications:", error);
    } finally {
      setIsLoadingExistingClassifications(false);
    }
  };

  const fetchExistingContacts = async () => {
    setIsLoadingContacts(true);
    try {
      const response = await fetch("http://localhost:8000/api/curate/get-contacts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setExistingOwners(data.owners || []);
        setExistingExperts(data.experts || []);
      } else {
        console.error("Failed to fetch contacts:", data.error);
      }
    } catch (error) {
      console.error("Error fetching contacts:", error);
    } finally {
      setIsLoadingContacts(false);
    }
  };

  const fetchExistingTags = async () => {
    setIsLoadingTags(true);
    try {
      const response = await fetch("http://localhost:8000/api/curate/get-tags", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setExistingTags(data.tags || []);
      } else {
        console.error("Failed to fetch tags:", data.error);
      }
    } catch (error) {
      console.error("Error fetching tags:", error);
    } finally {
      setIsLoadingTags(false);
    }
  };

  const handleAddTag = async () => {
    if (!addTagInput.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter a tag name",
        variant: "destructive",
      });
      return;
    }

    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/add-tags", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          tag: addTagInput.trim(),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setLastResult({
          success: true,
          message: ` Successfully added tag "${addTagInput}" to ${selectedAssets.length} asset(s)`,
        });
        toast({
          title: " Tag Added Successfully",
          description: `Tag "${addTagInput}" has been added to ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setAddTagInput("");
      } else {
        throw new Error(data.error || "Failed to add tag");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to add tag: ${errorMessage}`,
      });
      toast({
        title: " Error Adding Tag",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveTag = async () => {
    if (!removeTagInput.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter a tag name",
        variant: "destructive",
      });
      return;
    }

    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/remove-tags", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          tag: removeTagInput.trim(),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setLastResult({
          success: true,
          message: ` Successfully removed tag "${removeTagInput}" from ${selectedAssets.length} asset(s)`,
        });
        toast({
          title: " Tag Removed Successfully",
          description: `Tag "${removeTagInput}" has been removed from ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setRemoveTagInput("");
      } else {
        throw new Error(data.error || "Failed to remove tag");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to remove tag: ${errorMessage}`,
      });
      toast({
        title: " Error Removing Tag",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
      // Refresh tags after removal
      fetchExistingTags();
    }
  };

  const handleRemoveAllTags = async () => {
    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    if (existingTags.length === 0) {
      toast({
        title: "No Tags to Remove",
        description: "There are no tags on the selected assets",
        variant: "destructive",
      });
      return;
    }

    if (!confirm(`Are you sure you want to remove ALL tags from ${selectedAssets.length} asset(s)?`)) {
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      // Remove all tags one by one
      for (const tag of existingTags) {
        await fetch("http://localhost:8000/api/curate/remove-tags", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            guids: getGuids(),
            tag: tag,
          }),
        });
      }

      toast({
        title: " All Tags Removed Successfully",
        description: `Removed ${existingTags.length} tag(s) from ${selectedAssets.length} asset(s)`,
        duration: 5000,
        variant: "success" as any,
      });
      fetchExistingTags();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Error Removing Tags",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddOwner = async () => {
    if (!selectedOwner) {
      toast({
        title: "Validation Error",
        description: "Please select a user",
        variant: "destructive",
      });
      return;
    }

    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page or orphaned assets list",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/add-owner", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          contactType: "Owner",
          userId: selectedOwner,
          notes: ownerNotes,
          removeExisting: true,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Owner Added Successfully",
          description: `Owner has been added to ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setSelectedOwner("");
        setOwnerNotes("");
        // Refresh contacts and orphaned assets list
        fetchExistingContacts();
        if (orphanedAssets.length > 0) {
          await fetchOrphanedAssets();
        }
      } else {
        throw new Error(data.error || "Failed to add owner");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to add owner: ${errorMessage}`,
      });
      toast({
        title: " Error Adding Owner",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveSpecificOwner = async (ownerId: string, displayName: string) => {
    if (selectedAssets.length === 0) {
      return;
    }

    if (!confirm(`Are you sure you want to remove "${displayName}" as owner from ${selectedAssets.length} asset(s)?`)) {
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/remove-owner", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          contactType: "Owner",
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Owner Removed Successfully",
          description: `"${displayName}" has been removed as owner from ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        // Refresh contacts
        fetchExistingContacts();
      } else {
        throw new Error(data.error || "Failed to remove owner");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to remove owner: ${errorMessage}`,
      });
      toast({
        title: " Error Removing Owner",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveOwner = async () => {
    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    if (!confirm(`Are you sure you want to remove ALL owners from ${selectedAssets.length} asset(s)?`)) {
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/remove-owner", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          contactType: "Owner",
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Owner Removed Successfully",
          description: `Owner has been removed from ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        // Refresh contacts
        fetchExistingContacts();
      } else {
        throw new Error(data.error || "Failed to remove owner");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to remove owner: ${errorMessage}`,
      });
      toast({
        title: " Error Removing Owner",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveSpecificExpert = async (expertId: string, displayName: string) => {
    if (selectedAssets.length === 0) {
      return;
    }

    if (!confirm(`Are you sure you want to remove "${displayName}" as expert from ${selectedAssets.length} asset(s)?`)) {
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/remove-owner", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          contactType: "Expert",
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Expert Removed Successfully",
          description: `"${displayName}" has been removed as expert from ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        // Refresh contacts
        fetchExistingContacts();
      } else {
        throw new Error(data.error || "Failed to remove expert");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to remove expert: ${errorMessage}`,
      });
      toast({
        title: " Error Removing Expert",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddExpert = async () => {
    if (!selectedExpert) {
      toast({
        title: "Validation Error",
        description: "Please select a user",
        variant: "destructive",
      });
      return;
    }

    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page or orphaned assets list",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/add-owner", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          contactType: "Expert",
          userId: selectedExpert,
          notes: expertNotes,
          removeExisting: true,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Expert Added Successfully",
          description: `Expert has been added to ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setSelectedExpert("");
        setExpertNotes("");
        // Refresh contacts and orphaned assets list
        fetchExistingContacts();
        if (orphanedAssets.length > 0) {
          await fetchOrphanedAssets();
        }
      } else {
        throw new Error(data.error || "Failed to add expert");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to add expert: ${errorMessage}`,
      });
      toast({
        title: " Error Adding Expert",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveExpert = async () => {
    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    if (!confirm(`Are you sure you want to remove ALL experts from ${selectedAssets.length} asset(s)?`)) {
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/remove-owner", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          contactType: "Expert",
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Expert Removed Successfully",
          description: `Expert has been removed from ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        // Refresh contacts
        fetchExistingContacts();
      } else {
        throw new Error(data.error || "Failed to remove expert");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setLastResult({
        success: false,
        message: ` Failed to remove expert: ${errorMessage}`,
      });
      toast({
        title: " Error Removing Expert",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddClassifications = async () => {
    if (selectedClassifications.length === 0) {
      toast({
        title: "Validation Error",
        description: "Please select at least one classification",
        variant: "destructive",
      });
      return;
    }

    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/add-classifications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          classifications: selectedClassifications,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Classifications Added Successfully",
          description: `${selectedClassifications.length} classification(s) added to ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setSelectedClassifications([]);
        fetchExistingClassifications();
      } else {
        throw new Error(data.error || "Failed to add classifications");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Error Adding Classifications",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveClassifications = async () => {
    if (selectedClassifications.length === 0) {
      toast({
        title: "Validation Error",
        description: "Please select at least one classification",
        variant: "destructive",
      });
      return;
    }

    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/remove-classifications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          classifications: selectedClassifications,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Classifications Removed Successfully",
          description: `${selectedClassifications.length} classification(s) removed from ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setSelectedClassifications([]);
        fetchExistingClassifications();
      } else {
        throw new Error(data.error || "Failed to remove classifications");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Error Removing Classifications",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveAllClassifications = async () => {
    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to curate from the Assets page",
        variant: "destructive",
      });
      return;
    }

    if (existingClassifications.length === 0) {
      toast({
        title: "No Classifications to Remove",
        description: "There are no classifications on the selected assets",
        variant: "destructive",
      });
      return;
    }

    if (!confirm(`Are you sure you want to remove ALL ${existingClassifications.length} classifications from ${selectedAssets.length} asset(s)?`)) {
      return;
    }

    setIsSubmitting(true);
    setLastResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/curate/remove-classifications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          classifications: existingClassifications,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " All Classifications Removed Successfully",
          description: `Removed ${existingClassifications.length} classification(s) from ${selectedAssets.length} asset(s)`,
          duration: 5000,
          variant: "success" as any,
        });
        setSelectedClassifications([]);
        fetchExistingClassifications();
      } else {
        throw new Error(data.error || "Failed to remove all classifications");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Error Removing All Classifications",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleClassificationSelection = (classificationName: string) => {
    setSelectedClassifications(prev =>
      prev.includes(classificationName)
        ? prev.filter(c => c !== classificationName)
        : [...prev, classificationName]
    );
  };

  const handleAutoClassify = async () => {
    if (selectedAssets.length === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to analyze",
        variant: "destructive",
      });
      return;
    }

    setIsAutoClassifying(true);

    try {
      const response = await fetch("http://localhost:8000/api/curate/auto-classify", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          guids: getGuids(),
          apply: false,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setAutoClassificationSuggestions(data.suggestions);
        
        const totalColumns = data.total_columns || 0;
        const totalClassifications = data.total_classifications || 0;
        const totalAssets = data.total_assets || 0;
        
        if (totalClassifications > 0) {
          // If we have column-level suggestions, automatically fetch and show the schema
          if (totalColumns > 0) {
            // Fetch the schema data
            await fetchSchema();
            
            // Pre-populate columnClassifications with the AI suggestions
            const suggestions = data.suggestions || {};
            const newColumnClassifications: { [guid: string]: string[] } = {};
            
            Object.entries(suggestions).forEach(([entityGuid, entityData]: [string, any]) => {
              if (entityData.has_schema && entityData.classifications) {
                Object.entries(entityData.classifications).forEach(([columnGuid, columnInfo]: [string, any]) => {
                  if (columnInfo.classifications && columnInfo.classifications.length > 0) {
                    newColumnClassifications[columnGuid] = columnInfo.classifications;
                  }
                });
              }
            });
            
            setColumnClassifications(newColumnClassifications);
            setShowSchemaView(true);
            
            toast({
              title: " Analysis Complete",
              description: `Found ${totalClassifications} suggested classification(s) for ${totalColumns} column(s). Review the suggestions below and click Apply to save them.`,
              duration: 8000,
            });
          } else if (totalAssets > 0) {
            toast({
              title: " Analysis Complete", 
              description: `Found ${totalClassifications} suggested classification(s) for ${totalAssets} asset(s) (no schema available). Use the classification selection below to apply them.`,
              duration: 8000,
            });
          }
        } else {
          toast({
            title: "No Suggestions Found",
            description: "No automatic classifications could be suggested based on the asset/column names",
            duration: 5000,
          });
        }
      } else {
        throw new Error(data.error || "Failed to analyze assets");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Analysis Error",
        description: errorMessage,
        variant: "destructive",
        duration: 7000,
      });
    } finally {
      setIsAutoClassifying(false);
    }
  };

  // Lineage functions
  const fetchWorkspaces = async () => {
    setIsLoadingWorkspaces(true);
    try {
      const response = await fetch("http://localhost:8000/api/lineage/workspaces");
      const data = await response.json();

      if (response.ok && data.success) {
        setWorkspaces(data.workspaces || []);
        console.log("Loaded workspaces:", data.workspaces);
      } else {
        console.error("Failed to fetch workspaces:", data.error);
      }
    } catch (error) {
      console.error("Error fetching workspaces:", error);
    } finally {
      setIsLoadingWorkspaces(false);
    }
  };

  // Helper function to convert plain text to HTML
  const convertPlainTextToHtml = (plainText: string): string => {
    if (!plainText) return '';
    
    const lines = plainText.split('\n');
    let html = '';
    let inList = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      if (!line) {
        // Close list if we were in one
        if (inList) {
          html += '</ul>\n';
          inList = false;
        }
        continue;
      }
      
      // Detect bullet points
      if (line.startsWith('- ') || line.startsWith('• ') || line.startsWith('* ')) {
        if (!inList) {
          html += '<ul>\n';
          inList = true;
        }
        html += `<li>${line.substring(2).trim()}</li>\n`;
      }
      // Detect section headers (lines ending with colon or all caps short lines)
      else if (line.endsWith(':') || (line === line.toUpperCase() && line.length < 50)) {
        if (inList) {
          html += '</ul>\n';
          inList = false;
        }
        // Determine header level based on length and context
        if (line.length < 30) {
          html += `<h2>${line}</h2>\n`;
        } else {
          html += `<h3>${line}</h3>\n`;
        }
      }
      // Regular paragraph
      else {
        if (inList) {
          html += '</ul>\n';
          inList = false;
        }
        html += `<p>${line}</p>\n`;
      }
    }
    
    // Close list if still open
    if (inList) {
      html += '</ul>\n';
    }
    
    return html;
  };

  // Helper function to extract lakehouse tier from qualified name
  const extractLakehouseTier = (qualifiedName: string | undefined, assetName: string): string => {
    if (!qualifiedName) return "Unknown";
    
    const qn = qualifiedName.toLowerCase();
    const name = assetName.toLowerCase();
    
    // Check for Bronze/Silver/Gold pattern
    if (qn.includes('bronze') || name.includes('bronze')) return "Bronze";
    if (qn.includes('silver') || name.includes('silver')) return "Silver";
    if (qn.includes('gold') || name.includes('gold')) return "Gold";
    
    // Check for Landing/Base/Curated pattern
    if (qn.includes('landing') || name.includes('landing') || name.includes('raw')) return "Landing";
    if (qn.includes('base') || name.includes('base')) return "Base";
    if (qn.includes('curated') || name.includes('curated') || name.includes('refined')) return "Curated";
    
    return "Unknown";
  };

  // Helper function to get lakehouse name for a table
  const getLakehouseNameForTable = (table: any): string => {
    const qualifiedName = table.qualified_name || '';
    
    // Extract lakehouse GUID from qualified name pattern: .../lakehouses/{guid}/tables/...
    if (qualifiedName.includes('/lakehouses/')) {
      try {
        const lakehouseGuid = qualifiedName.split('/lakehouses/')[1].split('/')[0];
        
        // Find lakehouse with matching GUID
        if (discoveredLineage?.workspace_info?.lakehouses) {
          const lakehouse = discoveredLineage.workspace_info.lakehouses.find(
            (lh: any) => lh.guid === lakehouseGuid
          );
          if (lakehouse) {
            return lakehouse.name;
          }
        }
      } catch (e) {
        // If parsing fails, return Unknown
      }
    }
    
    return "Unknown";
  };

  const generateDescriptions = async () => {
    if (selectedDescriptionAssets.size === 0) {
      toast({
        title: "No Assets Selected",
        description: "Please select assets to generate descriptions for",
        variant: "destructive",
      });
      return;
    }

    setIsGeneratingDescription(true);
    setDescriptionResults([]);
    const results: Array<{guid: string; name: string; description: string; asset_type: string}> = [];

    try {
      // Find all selected assets from workspace info
      const allAssets: Array<{asset: any; type: string}> = [];
      
      if (discoveredLineage?.workspace_info) {
        const workspace = discoveredLineage.workspace_info;
        
        workspace.lakehouses?.forEach((lh: any) => {
          if (selectedDescriptionAssets.has(lh.guid)) {
            allAssets.push({asset: lh, type: 'lakehouse'});
          }
        });
        
        workspace.tables?.forEach((tbl: any) => {
          if (selectedDescriptionAssets.has(tbl.guid)) {
            allAssets.push({asset: tbl, type: 'table'});
          }
        });
        
        workspace.notebooks?.forEach((nb: any) => {
          if (selectedDescriptionAssets.has(nb.guid)) {
            allAssets.push({asset: nb, type: 'notebook'});
          }
        });
        
        workspace.warehouses?.forEach((wh: any) => {
          if (selectedDescriptionAssets.has(wh.guid)) {
            allAssets.push({asset: wh, type: 'warehouse'});
          }
        });
        
        workspace.files?.forEach((file: any) => {
          if (selectedDescriptionAssets.has(file.guid)) {
            allAssets.push({asset: file, type: 'file'});
          }
        });
        
        workspace.dataflows?.forEach((df: any) => {
          if (selectedDescriptionAssets.has(df.guid)) {
            allAssets.push({asset: df, type: 'dataflow'});
          }
        });
        
        workspace.pipelines?.forEach((pl: any) => {
          if (selectedDescriptionAssets.has(pl.guid)) {
            allAssets.push({asset: pl, type: 'pipeline'});
          }
        });
        
        workspace.other_assets?.forEach((oa: any) => {
          if (selectedDescriptionAssets.has(oa.guid)) {
            allAssets.push({asset: oa, type: oa.entity_type || 'asset'});
          }
        });
      }

      // Generate descriptions for each asset
      for (const {asset, type} of allAssets) {
        const payload: any = {
          asset_name: asset.name,
          asset_type: type,
          qualified_name: asset.qualified_name || "",
          guid: asset.guid,
        };

        if (type === "lakehouse" || type === "table") {
          payload.lakehouse_tier = extractLakehouseTier(asset.qualified_name, asset.name);
          // For tables, add lakehouse name
          if (type === "table") {
            payload.lakehouse_name = getLakehouseNameForTable(asset);
          }
        }

        if (type === "table" && asset.columns && asset.columns.length > 0) {
          payload.columns = asset.columns.map((col: any) => ({
            name: col.name,
            type: col.type,
          }));
        }

        try {
          const response = await fetch('http://localhost:8000/api/description/generate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
          });

          const result = await response.json();

          if (result.success && result.description) {
            results.push({
              guid: asset.guid,
              name: asset.name,
              description: result.description,
              asset_type: type
            });
          } else {
            console.error(`Failed to generate description for ${asset.name}:`, result.error || result.message || 'Unknown error');
          }
        } catch (error) {
          console.error(`Error generating description for ${asset.name}:`, error);
        }
      }

      setDescriptionResults(results);
      
      // Initialize editing state with HTML for backend and plain text for display
      const htmlState: {[guid: string]: string} = {};
      const plainTextState: {[guid: string]: string} = {};
      results.forEach(r => {
        htmlState[r.guid] = r.description; // Keep original HTML
        
        // Convert to plain text and remove title line containing asset name
        let plainText = r.description.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
        
        // Remove first line if it contains the asset name (e.g., "sales_customers Table Documentation")
        const lines = plainText.split('\n').map(line => line.trim()).filter(line => line.length > 0);
        if (lines.length > 0) {
          const firstLine = lines[0].toLowerCase();
          const assetNameLower = r.name.toLowerCase();
          
          // Remove first line if it contains the asset name
          if (firstLine.includes(assetNameLower)) {
            lines.shift();
          }
          plainText = lines.join('\n');
        }
        
        plainTextState[r.guid] = plainText;
      });
      setOriginalHtmlDescriptions(htmlState);
      setEditingDescriptions(plainTextState);

      toast({
        title: "Descriptions Generated",
        description: `Generated ${results.length} of ${selectedDescriptionAssets.size} descriptions`,
      });
    } catch (error) {
      console.error('Error generating descriptions:', error);
      toast({
        title: "Error",
        description: "Failed to generate descriptions",
        variant: "destructive",
      });
    } finally {
      setIsGeneratingDescription(false);
    }
  };

  const applyDescriptionsToPurview = async () => {
    if (descriptionResults.length === 0) return;

    setIsApplyingDescriptions(true);
    
    // Show initial feedback
    toast({
      title: "Applying Descriptions",
      description: `Updating ${descriptionResults.length} asset(s) in Microsoft Purview...`,
    });

    try {
      const response = await fetch('http://localhost:8000/api/description/apply', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          descriptions: descriptionResults.map(r => {
            // Always use the original HTML since we're just displaying plain text to user
            // The original HTML is what should be sent to Purview
            return {
              guid: r.guid,
              description: originalHtmlDescriptions[r.guid] || r.description
            };
          })
        }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: " Success!",
          description: `Successfully updated ${result.updated_count} of ${descriptionResults.length} asset(s) in Microsoft Purview`,
        });
        setDescriptionResults([]);
        setSelectedDescriptionAssets(new Set());
        setEditingDescriptions({});
        setOriginalHtmlDescriptions({});
      } else {
        toast({
          title: " Error",
          description: result.error || "Failed to apply descriptions",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error('Error applying descriptions:', error);
      toast({
        title: " Network Error",
        description: "Failed to connect to backend. Please check if the server is running.",
        variant: "destructive",
      });
    } finally {
      setIsApplyingDescriptions(false);
    }
  };

  // Fetch workspaces when component mounts (lineage doesn't require selected assets)
  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const handleDiscoverLineage = async () => {
    if (!selectedWorkspace) {
      toast({
        title: "No Workspace Selected",
        description: "Please select a workspace to discover lineage",
        variant: "destructive",
      });
      return;
    }

    setIsDiscoveringLineage(true);
    setDiscoveredLineage(null);
    setSelectedMappingIndices(new Set()); // Clear selection on new discovery
    setLineageMappings([]);

    try {
      const workspace = workspaces.find(w => w.workspace_id === selectedWorkspace);
      
      const response = await fetch("http://localhost:8000/api/lineage/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: selectedWorkspace,
          workspace_name: workspace?.workspace_name || "",
        }),
      });

      const data = await response.json();

      // Check if any lineage was actually found
      const hasLineageMappings = data.lineage?.lineage_mappings && data.lineage.lineage_mappings.length > 0;
      const hasUpstream = data.lineage?.upstream_assets && data.lineage.upstream_assets.length > 0;
      const hasDownstream = data.lineage?.downstream_assets && data.lineage.downstream_assets.length > 0;
      
      if (response.ok) {
        // Only set discovered lineage if we actually found something
        if (hasLineageMappings || hasUpstream || hasDownstream || data.success) {
          setDiscoveredLineage(data);
          
          // Auto-select all mappings by default
          if (hasLineageMappings) {
            const allIndices = new Set(data.lineage.lineage_mappings.map((_: any, idx: number) => idx));
            setSelectedMappingIndices(allIndices);
          }
          
          if (!hasLineageMappings && !hasUpstream && !hasDownstream) {
            // Backend returned success but no lineage found
            toast({
              title: " No Lineage Found",
              description: data.message || data.hint || "The AI agent could not discover valid lineage relationships for assets in this workspace.",
              variant: "destructive",
              duration: 7000,
            });
            setDiscoveredLineage(null); // Clear the state since nothing was found
            return;
          }
          
          const mappingCount = hasLineageMappings ? data.lineage.lineage_mappings.length : 0;
          const upstreamCount = data.lineage?.upstream_assets?.length || 0;
          const downstreamCount = data.lineage?.downstream_assets?.length || 0;
          
          toast({
            title: " Lineage Discovered",
            description: hasLineageMappings 
              ? `Found ${mappingCount} lineage mapping(s) with validated asset names`
              : `Found ${upstreamCount} upstream and ${downstreamCount} downstream assets`,
            duration: 5000,
          });
        } else {
          // No lineage found at all
          toast({
            title: " No Lineage Found",
            description: data.message || data.hint || "The AI agent could not discover valid lineage relationships for assets in this workspace.",
            variant: "destructive",
            duration: 7000,
          });
          setDiscoveredLineage(null);
        }
      } else {
        throw new Error(data.error || "Failed to discover lineage");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Discovery Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsDiscoveringLineage(false);
    }
  };

  const handleUpdateColumnMapping = (mappingIdx: number, colIdx: number, newTargetColumn: string) => {
    if (!discoveredLineage?.lineage?.lineage_mappings) return;
    
    const updatedLineage = { ...discoveredLineage };
    const updatedMappings = [...updatedLineage.lineage.lineage_mappings];
    const updatedMapping = { ...updatedMappings[mappingIdx] };
    const updatedColumnMappings = [...updatedMapping.column_mappings];
    
    updatedColumnMappings[colIdx] = {
      ...updatedColumnMappings[colIdx],
      target_column: newTargetColumn
    };
    
    updatedMapping.column_mappings = updatedColumnMappings;
    updatedMappings[mappingIdx] = updatedMapping;
    updatedLineage.lineage.lineage_mappings = updatedMappings;
    
    setDiscoveredLineage(updatedLineage);
  };

  const handleCreateLineage = async () => {
    // Use discovered lineage mappings if available
    const mappingsToCreate = discoveredLineage?.lineage?.lineage_mappings || lineageMappings;
    
    if (mappingsToCreate.length === 0) {
      toast({
        title: "No Mappings",
        description: "No lineage mappings to create",
        variant: "destructive",
      });
      return;
    }

    // Filter to only selected mappings
    const selectedMappings = mappingsToCreate.filter((_: any, idx: number) => selectedMappingIndices.has(idx));
    
    if (selectedMappings.length === 0) {
      toast({
        title: "No Mappings Selected",
        description: "Please select at least one mapping to create",
        variant: "destructive",
      });
      return;
    }

    setIsCreatingLineage(true);

    // Show initial progress toast
    toast({
      title: "⏳ Creating Lineage",
      description: `Creating ${selectedMappings.length} lineage relationship(s)...`,
      duration: 3000,
    });

    try {
      const response = await fetch("http://localhost:8000/api/lineage/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lineage_mappings: selectedMappings,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Count successes and failures
        const successCount = data.results?.filter((r: any) => r.success).length || 0;
        const failureCount = selectedMappings.length - successCount;
        
        // Build detailed description
        const details = data.results?.map((r: any, i: number) => {
          const mapping = selectedMappings[i];
          const source = mapping.source_table_name || 'Source';
          const target = mapping.target_table_name || 'Target';
          return r.success 
            ? ` ${source} → ${target}` 
            : ` ${source} → ${target}: ${r.error}`;
        }).join('\n') || data.message;
        
        // Store created lineages with process_guid for later deletion
        const newLineages = data.results
          ?.map((r: any, i: number) => {
            if (r.success && r.process_guid) {
              const mapping = selectedMappings[i];
              return {
                process_guid: r.process_guid,
                process_name: mapping.process_name || 'Data Flow',
                source_name: mapping.source_table_name || 'Source',
                target_name: mapping.target_table_name || 'Target',
              };
            }
            return null;
          })
          .filter((l: any) => l !== null) || [];
        
        if (newLineages.length > 0) {
          setCreatedLineages((prev) => [...newLineages, ...prev]);
        }
        
        toast({
          title: failureCount === 0 ? " Lineage Created Successfully" : " Lineage Created with Errors",
          description: `${successCount} of ${mappingsToCreate.length} relationship(s) created\n\n${details}`,
          variant: failureCount === 0 ? "default" : "destructive",
          duration: 7000,
        });
        
        // Clear manual mappings after successful creation
        if (successCount > 0) {
          setLineageMappings([]);
          // Don't clear discoveredLineage - keep it visible so user can create more or review
        }
      } else {
        throw new Error(data.error || "Failed to create lineage");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Creation Error",
        description: errorMessage,
        variant: "destructive",
        duration: 5000,
      });
    } finally {
      setIsCreatingLineage(false);
    }
  };

  const handleDeleteSelectedLineages = async () => {
    const selectedLineages = createdLineages.filter((_, idx) => selectedLineageIndices.has(idx));
    
    if (selectedLineages.length === 0) {
      toast({
        title: "No Lineages Selected",
        description: "Please select at least one lineage to delete",
        variant: "destructive",
      });
      return;
    }

    if (!confirm(`Delete ${selectedLineages.length} lineage relationship(s)? This will remove the process and its connections.`)) {
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/api/lineage/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lineage_mappings: selectedLineages.map(l => ({ process_guid: l.process_guid })),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast({
          title: " Lineage Deleted",
          description: data.message || `Deleted ${selectedLineages.length} lineage relationship(s)`,
          duration: 5000,
        });
        
        // Remove deleted lineages from state
        setCreatedLineages(prev => prev.filter((_, idx) => !selectedLineageIndices.has(idx)));
        setSelectedLineageIndices(new Set());
      } else {
        throw new Error(data.error || "Failed to delete lineages");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      toast({
        title: " Deletion Error",
        description: errorMessage,
        variant: "destructive",
        duration: 5000,
      });
    }
  };

  // Wrapper functions for Description tab (maps to existing description functions)
  const handleGenerateDescriptions = generateDescriptions;
  const handleApplyDescriptions = applyDescriptionsToPurview;
  const generatedDescriptions = descriptionResults;
  const isGeneratingDescriptions = isGeneratingDescription;

  return (
    <AppLayout title="Curate Assets">
      <div className="max-w-4xl mx-auto space-y-6 pt-6">
        {/* Selected Assets Summary - Hide for description, lineage, and glossary tabs */}
        {activeTab !== 'description' && activeTab !== 'lineage' && activeTab !== 'glossary' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="space-y-1.5">
                  <CardTitle>Selected Assets</CardTitle>
                  <CardDescription>
                    {selectedAssets.length === 0
                      ? "No assets selected. Go to the Assets page to select assets for curation."
                      : `${selectedAssets.length} asset(s) selected for curation`}
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                  className="gap-2"
                >
                  {showTechnicalDetails ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  {showTechnicalDetails ? "Hide" : "Show"} Technical Details
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {selectedAssets.length > 0 ? (
                <div className="space-y-3">
                  <div className="flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearAll}
                      className="text-destructive hover:text-destructive"
                    >
                      Clear All
                    </Button>
                  </div>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {selectedAssets.map((asset) => (
                      <div
                        key={asset.id}
                        className="flex items-center justify-between p-3 bg-muted/50 rounded-md"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{asset.name}</p>
                          {showTechnicalDetails && (
                            <p className="text-xs text-muted-foreground truncate">
                              {asset.qualifiedName || asset.id}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          <Badge variant="secondary" className="text-xs">
                            {asset.type}
                          </Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeAsset(asset.id)}
                            className="h-8 w-8 p-0"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Go to the Assets page and select assets using the checkboxes. Selected assets will appear here for bulk curation.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* Bulk Operations with Tabs */}
        <Card>
          <CardHeader>
            <CardTitle>Bulk Operations</CardTitle>
            <CardDescription>
              Enrich and manage metadata across multiple assets simultaneously
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="tags" className="w-full" onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="tags">
                  <Tag className="w-4 h-4 mr-2" />
                  Tags
                </TabsTrigger>
                <TabsTrigger value="contacts">
                  <Users className="w-4 h-4 mr-2" />
                  Contacts
                </TabsTrigger>
                <TabsTrigger value="classifications">
                  <Shield className="w-4 h-4 mr-2" />
                  Classifications
                </TabsTrigger>
                <TabsTrigger value="description">
                  <Database className="w-4 h-4 mr-2" />
                  Description
                </TabsTrigger>
                <TabsTrigger value="lineage">
                  <GitBranch className="w-4 h-4 mr-2" />
                  Data Lineage
                </TabsTrigger>
                <TabsTrigger value="glossary">
                  <BookOpen className="w-4 h-4 mr-2" />
                  Glossary
                </TabsTrigger>
              </TabsList>

              {/* Tags Tab */}
              <TabsContent value="tags" className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="tag-action">Action</Label>
                    <Select
                      value={tagAction}
                      onValueChange={(value) => setTagAction(value as 'add' | 'remove')}
                      disabled={isSubmitting || selectedAssets.length === 0}
                    >
                      <SelectTrigger id="tag-action">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="add">Add Tag</SelectItem>
                        <SelectItem value="remove">Remove Tag</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {tagAction === 'add' ? (
                    <>
                      <div className="space-y-2">
                        <Label htmlFor="add-tag-input">Tag Name</Label>
                        <div className="flex gap-2">
                          <Input
                            id="add-tag-input"
                            placeholder="Enter tag name (e.g., PII, Finance, Marketing)"
                            value={addTagInput}
                            onChange={(e) => setAddTagInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && !isSubmitting) {
                                handleAddTag();
                              }
                            }}
                            disabled={isSubmitting || selectedAssets.length === 0}
                            className="flex-1"
                          />
                          <Button
                            onClick={handleAddTag}
                            disabled={isSubmitting || !addTagInput.trim() || selectedAssets.length === 0}
                            className="min-w-[100px]"
                          >
                            {isSubmitting ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Adding...
                              </>
                            ) : (
                              <>
                                <Tag className="w-4 h-4 mr-2" />
                                Add Tag
                              </>
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          This tag will be added to all {selectedAssets.length} selected asset(s)
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      {/* Existing Tags Display */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Existing Tags on Selected Assets</Label>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={fetchExistingTags}
                            disabled={isLoadingTags || selectedAssets.length === 0}
                            className="h-8"
                          >
                            <RefreshCw className={`w-3 h-3 mr-1 ${isLoadingTags ? 'animate-spin' : ''}`} />
                            Refresh
                          </Button>
                        </div>
                  
                  {isLoadingTags ? (
                    <div className="flex items-center justify-center p-4 bg-muted/50 rounded-md">
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      <span className="text-sm text-muted-foreground">Loading tags...</span>
                    </div>
                  ) : existingTags.length > 0 ? (
                    <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-md">
                      {existingTags.map((tag) => (
                        <Badge
                          key={tag}
                          variant="secondary"
                          className="cursor-pointer hover:bg-secondary/80"
                          onClick={() => setRemoveTagInput(tag)}
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-muted/50 rounded-md">
                      <p className="text-sm text-muted-foreground text-center">
                        No tags found on selected assets
                      </p>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Click on a tag to select it for removal, or type manually below
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center space-x-2 p-3 bg-muted/30 rounded-md">
                    <input
                      type="checkbox"
                      id="remove-all-tags"
                      checked={removeTagInput === "__REMOVE_ALL__"}
                      onChange={(e) => setRemoveTagInput(e.target.checked ? "__REMOVE_ALL__" : "")}
                      disabled={isSubmitting || selectedAssets.length === 0 || existingTags.length === 0}
                      className="h-4 w-4"
                    />
                    <Label htmlFor="remove-all-tags" className="cursor-pointer font-normal">
                      Remove all {existingTags.length} tag(s) from selected assets
                    </Label>
                  </div>
                </div>

                {removeTagInput !== "__REMOVE_ALL__" && (
                  <div className="space-y-2">
                    <Label htmlFor="remove-tag-input">Tag Name</Label>
                    <Input
                      id="remove-tag-input"
                      placeholder="Enter tag name to remove or select from above"
                      value={removeTagInput}
                      onChange={(e) => setRemoveTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !isSubmitting) {
                          handleRemoveTag();
                        }
                      }}
                      disabled={isSubmitting || selectedAssets.length === 0}
                    />
                  </div>
                )}

                <Button
                  onClick={() => {
                    if (removeTagInput === "__REMOVE_ALL__") {
                      handleRemoveAllTags();
                    } else {
                      handleRemoveTag();
                    }
                  }}
                  disabled={isSubmitting || (removeTagInput !== "__REMOVE_ALL__" && !removeTagInput.trim()) || selectedAssets.length === 0}
                  variant="destructive"
                  className="w-full"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Removing...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4 mr-2" />
                      {removeTagInput === "__REMOVE_ALL__" 
                        ? `Remove All Tags (${existingTags.length})` 
                        : "Remove Tag"}
                    </>
                  )}
                </Button>
                <p className="text-xs text-muted-foreground">
                  {removeTagInput === "__REMOVE_ALL__" 
                    ? `All tags will be removed from ${selectedAssets.length} selected asset(s)` 
                    : `This tag will be removed from all ${selectedAssets.length} selected asset(s)`}
                </p>
                    </>
                  )}
                </div>
              </TabsContent>

              {/* Contacts Tab */}
              <TabsContent value="contacts" className="space-y-4">
                <div className="space-y-4">
                  {/* Orphaned Assets Button */}
                  <Button
                    variant="default"
                    className="w-full bg-amber-600 hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-600 text-white"
                    onClick={fetchOrphanedAssets}
                    disabled={isLoadingOrphanedAssets}
                  >
                    {isLoadingOrphanedAssets ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-4 h-4 mr-2" />
                        Find Orphaned Assets
                      </>
                    )}
                  </Button>

                  {/* Display Orphaned Assets */}
                  {orphanedAssets.length > 0 && (
                    <Card className="border-amber-200 dark:border-amber-800">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                          <AlertCircle className="w-5 h-5" />
                          Orphaned Assets ({orphanedAssets.length})
                        </CardTitle>
                        <CardDescription>
                          Assets with inactive owners or experts not found in Entra ID
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2 max-h-96 overflow-y-auto">
                          {orphanedAssets.map((asset) => (
                            <div
                              key={asset.id}
                              className="flex items-start gap-3 p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                            >
                              <Checkbox
                                checked={selectedAssets.some(a => a.id === asset.id)}
                                onCheckedChange={(checked) => {
                                  if (checked) {
                                    // Add to main selected assets context
                                    addAsset({
                                      id: asset.id,
                                      name: asset.name,
                                      type: asset.assetType,
                                    });
                                  } else {
                                    // Remove from main selected assets context
                                    removeAsset(asset.id);
                                  }
                                }}
                              />
                              <div className="flex-1 min-w-0">
                                <div className="font-medium truncate">{asset.name}</div>
                                <div className="flex items-center gap-2 mt-1">
                                  <Badge variant="outline" className="text-xs">
                                    {asset.assetType}
                                  </Badge>
                                  {asset.has_inactive_owner && (
                                    <Badge variant="destructive" className="text-xs">
                                      Inactive Owner
                                    </Badge>
                                  )}
                                  {asset.has_inactive_expert && (
                                    <Badge variant="destructive" className="text-xs">
                                      Inactive Expert
                                    </Badge>
                                  )}
                                </div>
                                <div className="text-xs text-muted-foreground mt-1 truncate">
                                  {asset.id}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                        {selectedAssets.some(sa => orphanedAssets.some(oa => oa.id === sa.id)) && (
                          <div className="mt-4 p-3 bg-muted rounded-lg">
                            <p className="text-sm font-medium mb-2">
                              {selectedAssets.filter(sa => orphanedAssets.some(oa => oa.id === sa.id)).length} orphaned asset(s) added to selection
                            </p>
                            <p className="text-xs text-muted-foreground">
                              These assets now appear in "Selected Assets for Curation" above. Use the contact controls below to assign new owners or experts.
                            </p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="contact-type">Contact Type</Label>
                      <Select
                        value={contactType}
                        onValueChange={(value) => setContactType(value as 'owner' | 'expert' | 'both')}
                        disabled={isSubmitting || selectedAssets.length === 0}
                      >
                        <SelectTrigger id="contact-type">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="owner">
                            <div className="flex items-center">
                              <User className="w-4 h-4 mr-2" />
                              Owner
                            </div>
                          </SelectItem>
                          <SelectItem value="expert">
                            <div className="flex items-center">
                              <UserCog className="w-4 h-4 mr-2" />
                              Expert
                            </div>
                          </SelectItem>
                          <SelectItem value="both">
                            <div className="flex items-center">
                              <Users className="w-4 h-4 mr-2" />
                              Both (Owner & Expert)
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="contact-action">Action</Label>
                      <Select
                        value={contactAction}
                        onValueChange={(value) => setContactAction(value as 'add' | 'remove')}
                        disabled={isSubmitting || selectedAssets.length === 0}
                      >
                        <SelectTrigger id="contact-action">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="add">Add Contact</SelectItem>
                          <SelectItem value="remove">Remove Contact</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {contactAction === 'add' ? (
                    <>
                      {/* Display current contacts */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Current Contacts on Selected Assets</Label>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={fetchExistingContacts}
                            disabled={isLoadingContacts || selectedAssets.length === 0}
                            className="h-8"
                          >
                            <RefreshCw className={`w-3 h-3 mr-1 ${isLoadingContacts ? 'animate-spin' : ''}`} />
                            Refresh
                          </Button>
                        </div>
                        
                        {isLoadingContacts ? (
                          <div className="flex items-center justify-center p-4 bg-muted/50 rounded-md">
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            <span className="text-sm text-muted-foreground">Loading contacts...</span>
                          </div>
                        ) : (existingOwners.length > 0 || existingExperts.length > 0) ? (
                          <div className="space-y-2">
                            <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-md">
                              {[...existingOwners.map(o => ({...o, type: 'owner' as const})), ...existingExperts.map(e => ({...e, type: 'expert' as const}))].map((contact) => (
                                <Badge
                                  key={`${contact.type}-${contact.id}`}
                                  variant="secondary"
                                  className={`${contact.type === 'owner' ? 'bg-blue-100 dark:bg-blue-950' : 'bg-purple-100 dark:bg-purple-950'}`}
                                >
                                  {contact.type === 'owner' ? (
                                    <User className="w-3 h-3 mr-1" />
                                  ) : (
                                    <UserCog className="w-3 h-3 mr-1" />
                                  )}
                                  {contact.displayName}
                                  <span className="mx-1 text-xs opacity-60">({contact.type === 'owner' ? 'Owner' : 'Expert'})</span>
                                </Badge>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="p-4 bg-muted/50 rounded-md">
                            <p className="text-sm text-muted-foreground text-center">
                              No contacts found on selected assets
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="contact-select">Select User</Label>
                        <Select
                          value={contactType === 'both' ? selectedOwner : contactType === 'owner' ? selectedOwner : selectedExpert}
                          onValueChange={(value) => {
                            if (contactType === 'both') {
                              setSelectedOwner(value);
                              setSelectedExpert(value);
                            } else if (contactType === 'owner') {
                              setSelectedOwner(value);
                            } else {
                              setSelectedExpert(value);
                            }
                          }}
                          disabled={isSubmitting || isLoadingUsers || selectedAssets.length === 0}
                        >
                          <SelectTrigger id="contact-select">
                            <SelectValue placeholder={isLoadingUsers ? "Loading users..." : "Select a user"} />
                          </SelectTrigger>
                          <SelectContent>
                            {users.map((user) => (
                              <SelectItem key={user.id} value={user.id}>
                                {user.displayName}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="contact-notes">Notes (Optional)</Label>
                        <Textarea
                          id="contact-notes"
                          placeholder={contactType === 'both' ? 'Add notes about the contact' : `Add notes about the ${contactType}`}
                          value={contactType === 'both' ? ownerNotes : contactType === 'owner' ? ownerNotes : expertNotes}
                          onChange={(e) => {
                            if (contactType === 'both') {
                              setOwnerNotes(e.target.value);
                              setExpertNotes(e.target.value);
                            } else if (contactType === 'owner') {
                              setOwnerNotes(e.target.value);
                            } else {
                              setExpertNotes(e.target.value);
                            }
                          }}
                          disabled={isSubmitting || selectedAssets.length === 0}
                          rows={3}
                        />
                      </div>

                      <Button
                        onClick={async () => {
                          if (contactType === 'both') {
                            await handleAddOwner();
                            await handleAddExpert();
                          } else if (contactType === 'owner') {
                            await handleAddOwner();
                          } else {
                            await handleAddExpert();
                          }
                        }}
                        disabled={isSubmitting || (contactType === 'both' ? (!selectedOwner || !selectedExpert) : contactType === 'owner' ? !selectedOwner : !selectedExpert) || selectedAssets.length === 0}
                        className="w-full"
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Adding...
                          </>
                        ) : (
                          <>
                            {contactType === 'both' ? (
                              <Users className="w-4 h-4 mr-2" />
                            ) : contactType === 'owner' ? (
                              <User className="w-4 h-4 mr-2" />
                            ) : (
                              <UserCog className="w-4 h-4 mr-2" />
                            )}
                            Add {contactType === 'both' ? 'Owner & Expert' : contactType === 'owner' ? 'Owner' : 'Expert'}
                          </>
                        )}
                      </Button>
                      <p className="text-xs text-muted-foreground">
                        {contactType === 'both' ? (
                          <>This user will be added as both owner and expert to all {selectedAssets.length} selected asset(s)</>
                        ) : (
                          <>This {contactType} will be added to all {selectedAssets.length} selected asset(s)</>
                        )}
                      </p>
                    </>
                  ) : (
                    <>
                      {/* Display existing contacts */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Current Contacts on Selected Assets</Label>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={fetchExistingContacts}
                            disabled={isLoadingContacts || selectedAssets.length === 0}
                            className="h-8"
                          >
                            <RefreshCw className={`w-3 h-3 mr-1 ${isLoadingContacts ? 'animate-spin' : ''}`} />
                            Refresh
                          </Button>
                        </div>
                        
                        {isLoadingContacts ? (
                          <div className="flex items-center justify-center p-4 bg-muted/50 rounded-md">
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            <span className="text-sm text-muted-foreground">Loading contacts...</span>
                          </div>
                        ) : (existingOwners.length > 0 || existingExperts.length > 0) ? (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground">
                              Click on a contact to remove them individually
                            </p>
                            <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-md">
                              {[...existingOwners.map(o => ({...o, type: 'owner' as const})), ...existingExperts.map(e => ({...e, type: 'expert' as const}))].map((contact) => (
                                <Badge
                                  key={`${contact.type}-${contact.id}`}
                                  variant="secondary"
                                  className={`cursor-pointer hover:bg-destructive hover:text-destructive-foreground transition-colors ${contact.type === 'owner' ? 'bg-blue-100 dark:bg-blue-950' : 'bg-purple-100 dark:bg-purple-950'}`}
                                  onClick={() => contact.type === 'owner' ? handleRemoveSpecificOwner(contact.id, contact.displayName) : handleRemoveSpecificExpert(contact.id, contact.displayName)}
                                >
                                  {contact.type === 'owner' ? (
                                    <User className="w-3 h-3 mr-1" />
                                  ) : (
                                    <UserCog className="w-3 h-3 mr-1" />
                                  )}
                                  {contact.displayName}
                                  <span className="mx-1 text-xs opacity-60">({contact.type === 'owner' ? 'Owner' : 'Expert'})</span>
                                  <X className="w-3 h-3 ml-1" />
                                </Badge>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="p-4 bg-muted/50 rounded-md">
                            <p className="text-sm text-muted-foreground text-center">
                              No contacts found on selected assets
                            </p>
                          </div>
                        )}
                      </div>
                      
                      <Button
                        onClick={async () => {
                          if (contactType === 'both') {
                            await handleRemoveOwner();
                            await handleRemoveExpert();
                          } else if (contactType === 'owner') {
                            await handleRemoveOwner();
                          } else {
                            await handleRemoveExpert();
                          }
                        }}
                        disabled={isSubmitting || selectedAssets.length === 0 || (contactType === 'both' ? (existingOwners.length === 0 && existingExperts.length === 0) : (contactType === 'owner' ? existingOwners : existingExperts).length === 0)}
                        variant="destructive"
                        className="w-full"
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Removing...
                          </>
                        ) : (
                          <>
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove All {contactType === 'both' ? 'Contacts' : contactType === 'owner' ? 'Owners' : 'Experts'}
                          </>
                        )}
                      </Button>
                      <p className="text-xs text-muted-foreground">
                        {contactType === 'both' ? (
                          <>This will remove ALL owners and experts from all {selectedAssets.length} selected asset(s)</>
                        ) : (
                          <>This will remove ALL {contactType === 'owner' ? 'owners' : 'experts'} from all {selectedAssets.length} selected asset(s)</>
                        )}
                      </p>
                    </>
                  )}
                </div>
              </TabsContent>

              {/* Classifications Tab */}
              <TabsContent value="classifications" className="space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="classification-action">Action</Label>
                    <Select
                      value={classificationAction}
                      onValueChange={(value) => setClassificationAction(value as 'add' | 'remove')}
                      disabled={isSubmitting || selectedAssets.length === 0}
                    >
                      <SelectTrigger id="classification-action">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="add">Add Classifications</SelectItem>
                        <SelectItem value="remove">Remove Classifications</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {classificationAction === 'add' ? (
                    <>
                      {/* Display existing classifications */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Current Classifications on Selected Assets</Label>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={fetchExistingClassifications}
                            disabled={isLoadingExistingClassifications || selectedAssets.length === 0}
                            className="h-8"
                          >
                            <RefreshCw className={`w-3 h-3 mr-1 ${isLoadingExistingClassifications ? 'animate-spin' : ''}`} />
                            Refresh
                          </Button>
                        </div>
                        
                        {isLoadingExistingClassifications ? (
                          <div className="flex items-center justify-center p-4 bg-muted/50 rounded-md">
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            <span className="text-sm text-muted-foreground">Loading classifications...</span>
                          </div>
                        ) : existingClassifications.length > 0 ? (
                          <div className="flex flex-wrap gap-2 p-4 bg-muted/50 rounded-md border border-border max-h-40 overflow-y-auto">
                            {existingClassifications.map((classification) => (
                              <Badge
                                key={classification}
                                variant="secondary"
                                className="bg-purple-600 dark:bg-purple-700 text-white text-sm px-3 py-1"
                                title={classification}
                              >
                                {getClassificationDisplayName(classification)}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <div className="p-4 bg-muted/50 rounded-md">
                            <p className="text-sm text-muted-foreground text-center">
                              No classifications found on selected assets
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Auto-Classify Section */}
                      <div className="space-y-2 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
                        <div className="flex items-start justify-between">
                          <div className="space-y-1">
                            <Label className="text-base font-semibold flex items-center gap-2">
                              <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                              AI-Powered Column Classification
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              Automatically analyze assets and suggest classifications for columns (if schema available) or assets
                            </p>
                          </div>
                        </div>
                        <Button
                          onClick={() => handleAutoClassify()}
                          disabled={isAutoClassifying || isSubmitting || selectedAssets.length === 0}
                          className="w-full"
                        >
                          {isAutoClassifying ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Analyzing...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-4 h-4 mr-2" />
                              Analyze & Suggest Classifications
                            </>
                          )}
                        </Button>
                        <p className="text-xs text-muted-foreground">
                          Analyzes column names (if schema available) or asset names and suggests appropriate classifications. Review suggestions and use manual classification to apply them.
                        </p>
                      </div>

                      {/* Manual Schema Classification Section */}
                      <div className="space-y-2 p-4 bg-gradient-to-r from-green-50 to-teal-50 dark:from-green-950/20 dark:to-teal-950/20 rounded-lg border border-green-200 dark:border-green-800">
                        <div className="flex items-start justify-between">
                          <div className="space-y-1">
                            <Label className="text-base font-semibold flex items-center gap-2">
                              <Shield className="w-4 h-4 text-green-600 dark:text-green-400" />
                              Manual Column Classification
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              View schema and manually select classifications for each column
                            </p>
                          </div>
                        </div>
                        <Button
                          onClick={fetchSchema}
                          disabled={isLoadingSchema || isSubmitting || selectedAssets.length === 0}
                          variant="outline"
                          className="w-full"
                        >
                          {isLoadingSchema ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Loading Schema...
                            </>
                          ) : (
                            <>
                              <Shield className="w-4 h-4 mr-2" />
                              View Schema & Classify Columns
                            </>
                          )}
                        </Button>
                      </div>

                      {/* Schema View Modal/Panel */}
                      {showSchemaView && Object.keys(schemaData).length > 0 && (
                        <div className="space-y-4 p-4 border-2 border-blue-300 dark:border-blue-700 rounded-lg bg-blue-50/50 dark:bg-blue-950/20">
                          <div className="flex items-center justify-between">
                            <h3 className="text-lg font-semibold">Schema & Column Classifications</h3>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setShowSchemaView(false)}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                          
                          {Object.entries(schemaData).map(([guid, data]) => {
                            const asset = selectedAssets.find(a => a.id === guid);
                            if (!data.has_schema || !data.schema || data.schema.length === 0) {
                              return (
                                <div key={guid} className="p-3 bg-yellow-50 dark:bg-yellow-950/20 rounded border border-yellow-200">
                                  <p className="text-sm font-medium">{asset?.name || guid}</p>
                                  <p className="text-xs text-muted-foreground">No schema available for this asset</p>
                                </div>
                              );
                            }
                            
                            return (
                              <div key={guid} className="space-y-3">
                                <div className="flex items-center gap-2 pb-2 border-b">
                                  <h4 className="font-semibold text-base">{asset?.name || guid}</h4>
                                  <Badge variant="outline" className="text-[10px]">{data.schema.length} columns</Badge>
                                </div>
                                <div className="space-y-3">
                                  {data.schema.map((column) => {
                                    // Check if this column has AI suggestions
                                    const hasAISuggestion = autoClassificationSuggestions && 
                                      autoClassificationSuggestions[guid]?.classifications?.[column.guid];
                                    
                                    // Get existing classifications on this column
                                    const existingClassifications = column.existing_classifications || [];
                                    
                                    return (
                                      <div key={column.guid} className="group hover:shadow-md transition-shadow">
                                        <div className="p-4 bg-card rounded-lg border border-border space-y-2">
                                          {/* Column name and type */}
                                          <div className="flex items-center gap-2">
                                            <p className="text-sm font-semibold text-foreground">{column.name}</p>
                                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                                              {column.type.replace('fabric_lakehouse_table_column', 'Column').replace('_', ' ')}
                                            </Badge>
                                          </div>
                                          
                                          {/* AI suggestions */}
                                          {hasAISuggestion && (
                                            <div className="flex items-start gap-1.5 text-xs text-blue-600 dark:text-blue-400">
                                              <Sparkles className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                                              <span className="font-medium">AI Suggested: {hasAISuggestion.classifications.join(', ')}</span>
                                            </div>
                                          )}
                                          
                                          {/* Current and Select on same line */}
                                          <div className="flex items-stretch gap-3">
                                            {/* Show existing classifications */}
                                            <div className="flex-1 min-w-0">
                                              {existingClassifications.length > 0 ? (
                                                <div className="min-h-[42px] p-2.5 bg-muted/50 rounded-md border border-border">
                                                  <div className="flex flex-wrap gap-1.5 items-center">
                                                    <span className="text-xs font-medium text-muted-foreground">Current:</span>
                                                    {existingClassifications.map((cls, idx) => (
                                                      <Badge key={idx} variant="secondary" className="text-xs px-2 py-0.5 bg-purple-600 dark:bg-purple-700 text-white">
                                                        {getClassificationDisplayName(cls)}
                                                      </Badge>
                                                    ))}
                                                  </div>
                                                </div>
                                              ) : (
                                                <div className="min-h-[42px] flex items-center">
                                                  <span className="text-xs text-muted-foreground">No current classifications</span>
                                                </div>
                                              )}
                                            </div>
                                            
                                            {/* Select classification dropdown */}
                                            <div className="w-72 flex-shrink-0 flex items-stretch">
                                              <Select
                                                value={columnClassifications[column.guid]?.[0] || existingClassifications[0] || ""}
                                                onValueChange={(value) => {
                                                  setColumnClassifications(prev => ({
                                                    ...prev,
                                                    [column.guid]: value ? [value] : []
                                                  }));
                                                }}
                                              >
                                                <SelectTrigger className="min-h-[42px] text-sm font-medium">
                                                  <SelectValue placeholder="Select classification..." />
                                                </SelectTrigger>
                                                <SelectContent>
                                                  {classifications.map((classification) => (
                                                    <SelectItem key={classification.name} value={classification.name} className="text-xs">
                                                      {getClassificationDisplayName(classification.name)}
                                                    </SelectItem>
                                                  ))}
                                                </SelectContent>
                                              </Select>
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          })}
                          
                          <Button
                            onClick={applyColumnClassifications}
                            disabled={isSubmitting || Object.keys(columnClassifications).length === 0}
                            className="w-full"
                          >
                            {isSubmitting ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Applying...
                              </>
                            ) : (
                              <>
                                <Shield className="w-4 h-4 mr-2" />
                                Apply Classifications to {Object.keys(columnClassifications).length} Column(s)
                              </>
                            )}
                          </Button>
                        </div>
                      )}

                      {/* Classification selection */}
                      <div className="space-y-2">
                        <Label htmlFor="classification-search">Search and Select Classifications</Label>
                        <Input
                          id="classification-search"
                          placeholder="Search classifications..."
                          value={classificationSearchTerm}
                          onChange={(e) => setClassificationSearchTerm(e.target.value)}
                          disabled={isSubmitting || selectedAssets.length === 0}
                        />
                        
                        {isLoadingClassifications ? (
                          <div className="flex items-center justify-center p-4 bg-muted/50 rounded-md">
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            <span className="text-sm text-muted-foreground">Loading classifications...</span>
                          </div>
                        ) : (
                          <div className="border rounded-md p-3 max-h-64 overflow-y-auto space-y-1">
                            {classifications
                              .filter(c => 
                                c.name.toLowerCase().includes(classificationSearchTerm.toLowerCase()) ||
                                c.description?.toLowerCase().includes(classificationSearchTerm.toLowerCase())
                              )
                              .map((classification) => (
                                <div
                                  key={classification.name}
                                  className={`flex items-start space-x-2 p-2 rounded-md cursor-pointer hover:bg-muted/50 ${
                                    selectedClassifications.includes(classification.name) ? 'bg-primary/10' : ''
                                  }`}
                                  onClick={() => toggleClassificationSelection(classification.name)}
                                >
                                  <input
                                    type="checkbox"
                                    checked={selectedClassifications.includes(classification.name)}
                                    onChange={() => {}}
                                    className="mt-1"
                                  />
                                  <div className="flex-1">
                                    <div className="font-medium text-sm" title={classification.name}>
                                      {getClassificationDisplayName(classification.name)}
                                    </div>
                                    {classification.description && (
                                      <div className="text-xs text-muted-foreground">
                                        {classification.description}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            {classifications.filter(c => 
                              c.name.toLowerCase().includes(classificationSearchTerm.toLowerCase()) ||
                              c.description?.toLowerCase().includes(classificationSearchTerm.toLowerCase())
                            ).length === 0 && (
                              <div className="p-4 text-center text-sm text-muted-foreground">
                                No classifications found
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Selected classifications */}
                      {selectedClassifications.length > 0 && (
                        <div className="space-y-2">
                          <Label>Selected Classifications ({selectedClassifications.length})</Label>
                          <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-md">
                            {selectedClassifications.map((classification) => (
                              <Badge
                                key={classification}
                                variant="secondary"
                                className="cursor-pointer hover:bg-secondary/80 bg-green-100 dark:bg-green-950"
                                onClick={() => toggleClassificationSelection(classification)}
                                title={classification}
                              >
                                {getClassificationDisplayName(classification)}
                                <X className="w-3 h-3 ml-1" />
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      <Button
                        onClick={handleAddClassifications}
                        disabled={isSubmitting || selectedClassifications.length === 0 || selectedAssets.length === 0}
                        className="w-full"
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Adding...
                          </>
                        ) : (
                          <>
                            <Shield className="w-4 h-4 mr-2" />
                            Add {selectedClassifications.length} Classification(s)
                          </>
                        )}
                      </Button>
                      <p className="text-xs text-muted-foreground">
                        {selectedClassifications.length} classification(s) will be added to all {selectedAssets.length} selected asset(s)
                      </p>
                    </>
                  ) : (
                    <>
                      {/* Display existing classifications for removal */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Label>Current Classifications on Selected Assets</Label>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={fetchExistingClassifications}
                            disabled={isLoadingExistingClassifications || selectedAssets.length === 0}
                            className="h-8"
                          >
                            <RefreshCw className={`w-3 h-3 mr-1 ${isLoadingExistingClassifications ? 'animate-spin' : ''}`} />
                            Refresh
                          </Button>
                        </div>
                        
                        <p className="text-xs text-muted-foreground">
                          Click on classifications to select them for removal
                        </p>
                        
                        {isLoadingExistingClassifications ? (
                          <div className="flex items-center justify-center p-4 bg-muted/50 rounded-md">
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            <span className="text-sm text-muted-foreground">Loading classifications...</span>
                          </div>
                        ) : existingClassifications.length > 0 ? (
                          <div className="border rounded-md p-3 max-h-64 overflow-y-auto space-y-1">
                            {existingClassifications.map((classification) => (
                              <div
                                key={classification}
                                className={`flex items-start space-x-2 p-2 rounded-md cursor-pointer hover:bg-muted/50 ${
                                  selectedClassifications.includes(classification) ? 'bg-destructive/10' : ''
                                }`}
                                onClick={() => toggleClassificationSelection(classification)}
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedClassifications.includes(classification)}
                                  onChange={() => {}}
                                  className="mt-1"
                                />
                                <div className="flex-1">
                                  <div className="font-medium text-sm" title={classification}>
                                    {getClassificationDisplayName(classification)}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="p-4 bg-muted/50 rounded-md">
                            <p className="text-sm text-muted-foreground text-center">
                              No classifications found on selected assets
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center space-x-2 p-3 bg-muted/30 rounded-md">
                          <input
                            type="checkbox"
                            id="remove-all-classifications"
                            checked={selectedClassifications.length === existingClassifications.length && existingClassifications.length > 0}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedClassifications([...existingClassifications]);
                              } else {
                                setSelectedClassifications([]);
                              }
                            }}
                            disabled={isSubmitting || selectedAssets.length === 0 || existingClassifications.length === 0}
                            className="h-4 w-4"
                          />
                          <Label htmlFor="remove-all-classifications" className="cursor-pointer font-normal">
                            Select all {existingClassifications.length} classification(s) for removal
                          </Label>
                        </div>
                      </div>

                      {/* Selected classifications for removal */}
                      {selectedClassifications.length > 0 && (
                        <div className="space-y-2">
                          <Label>Selected for Removal ({selectedClassifications.length})</Label>
                          <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-md max-h-32 overflow-y-auto">
                            {selectedClassifications.map((classification) => (
                              <Badge
                                key={classification}
                                variant="secondary"
                                className="cursor-pointer hover:bg-secondary/80 bg-red-100 dark:bg-red-950"
                                onClick={() => toggleClassificationSelection(classification)}
                                title={classification}
                              >
                                {getClassificationDisplayName(classification)}
                                <X className="w-3 h-3 ml-1" />
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      <Button
                        onClick={selectedClassifications.length === existingClassifications.length && existingClassifications.length > 0 ? handleRemoveAllClassifications : handleRemoveClassifications}
                        disabled={isSubmitting || selectedClassifications.length === 0 || selectedAssets.length === 0}
                        variant="destructive"
                        className="w-full"
                      >
                        {isSubmitting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Removing...
                          </>
                        ) : (
                          <>
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove {selectedClassifications.length} Classification(s)
                          </>
                        )}
                      </Button>
                      <p className="text-xs text-muted-foreground">
                        {selectedClassifications.length} classification(s) will be removed from all {selectedAssets.length} selected asset(s)
                      </p>
                    </>
                  )}
                </div>
              </TabsContent>

              {/* Workspace Browser Tab */}
              <TabsContent value="description" className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-start gap-2 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <Database className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div className="space-y-2 flex-1">
                      <p className="text-sm text-blue-900 dark:text-blue-100 font-medium">
                        Browse Fabric Workspace Assets
                      </p>
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        Select a Fabric workspace to view all its assets including lakehouses, tables, notebooks, and more. 
                        You can explore the workspace structure and add assets to your curation list.
                      </p>
                    </div>
                  </div>

                  {/* Workspace Selection */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="browse-workspace-select">Select Fabric Workspace</Label>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={fetchWorkspaces}
                        disabled={isLoadingWorkspaces}
                      >
                        <RefreshCw className={`w-3 h-3 ${isLoadingWorkspaces ? 'animate-spin' : ''}`} />
                      </Button>
                    </div>
                    <Select
                      value={selectedWorkspace}
                      onValueChange={setSelectedWorkspace}
                      disabled={isLoadingWorkspaces}
                    >
                      <SelectTrigger id="browse-workspace-select">
                        <SelectValue placeholder={isLoadingWorkspaces ? "Loading workspaces..." : "Choose a workspace to browse"} />
                      </SelectTrigger>
                      <SelectContent>
                        {workspaces.map((workspace) => (
                          <SelectItem key={workspace.workspace_id} value={workspace.workspace_id}>
                            <div className="flex items-center justify-between w-full">
                              <span>{workspace.workspace_name}</span>
                              <Badge variant="secondary" className="ml-2">
                                {workspace.asset_count} assets
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      {workspaces.length} workspace(s) available with Fabric assets
                    </p>
                  </div>

                  {/* Load Workspace Assets Button */}
                  {selectedWorkspace && (
                    <Button
                      onClick={async () => {
                        try {
                          setIsDiscoveringLineage(true);
                          const selectedWS = workspaces.find(w => w.workspace_id === selectedWorkspace);
                          
                          const response = await fetch('http://localhost:8000/api/lineage/workspace-assets', {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                              workspace_id: selectedWorkspace,
                              workspace_name: selectedWS?.workspace_name || selectedWorkspace,
                            }),
                          });

                          const result = await response.json();
                          
                          if (result.success && result.workspace_info) {
                            // For description tab, we just want the workspace assets, not lineage
                            setDiscoveredLineage({
                              success: true,
                              workspace_info: result.workspace_info,
                              lineage_mappings: []  // No lineage needed for description
                            });
                            toast({
                              title: "Workspace Loaded",
                              description: `Loaded ${result.workspace_info.total_assets || 0} assets from ${selectedWS?.workspace_name}`,
                            });
                          } else {
                            toast({
                              title: "Error",
                              description: result.error || result.message || "Failed to load workspace",
                              variant: "destructive",
                            });
                          }
                        } catch (error) {
                          console.error('Error loading workspace:', error);
                          toast({
                            title: "Error",
                            description: "Failed to load workspace assets",
                            variant: "destructive",
                          });
                        } finally {
                          setIsDiscoveringLineage(false);
                        }
                      }}
                      disabled={isDiscoveringLineage}
                      className="w-full"
                    >
                      {isDiscoveringLineage ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Loading Assets...
                        </>
                      ) : (
                        <>
                          <Database className="w-4 h-4 mr-2" />
                          Load Workspace Assets
                        </>
                      )}
                    </Button>
                  )}

                  {/* Display Workspace Assets */}
                  {discoveredLineage?.workspace_info && (
                    <div className="space-y-4 mt-6">
                      <div className="flex items-center justify-between">
                        <Label className="text-lg font-semibold">
                          Workspace: {discoveredLineage.workspace_info.workspace_name}
                        </Label>
                      </div>

                      {/* Lakehouses */}
                      {discoveredLineage.workspace_info.lakehouses && discoveredLineage.workspace_info.lakehouses.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <Database className="w-5 h-5" />
                              Lakehouses ({discoveredLineage.workspace_info.lakehouses.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              {discoveredLineage.workspace_info.lakehouses.map((lakehouse: any, idx: number) => (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(lakehouse.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(lakehouse.guid);
                                        } else {
                                          newSet.delete(lakehouse.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="font-medium truncate">{lakehouse.name}</div>
                                      {showTechnicalDetails && (
                                        <>
                                          <div className="text-xs text-muted-foreground mt-1 truncate">
                                            GUID: {lakehouse.guid}
                                          </div>
                                          {lakehouse.qualified_name && (
                                            <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                              {lakehouse.qualified_name}
                                            </div>
                                          )}
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Tables */}
                      {discoveredLineage.workspace_info.tables && discoveredLineage.workspace_info.tables.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <FileText className="w-5 h-5" />
                              Lakehouse Tables ({discoveredLineage.workspace_info.tables.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2 max-h-96 overflow-y-auto">
                              {discoveredLineage.workspace_info.tables.map((table: any, idx: number) => {
                                const lakehouseName = getLakehouseNameForTable(table);
                                return (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(table.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(table.guid);
                                        } else {
                                          newSet.delete(table.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-2 min-w-0">
                                        <div className="font-medium truncate">{table.name}</div>
                                        {lakehouseName !== "Unknown" && (
                                          <Badge variant="secondary" className="text-xs flex-shrink-0">
                                            {lakehouseName}
                                          </Badge>
                                        )}
                                      </div>
                                      {showTechnicalDetails && (
                                        <>
                                          <div className="text-xs text-muted-foreground mt-1 truncate">
                                            GUID: {table.guid}
                                          </div>
                                          {table.qualified_name && (
                                            <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                              {table.qualified_name}
                                            </div>
                                          )}
                                        </>
                                      )}
                                      {table.columns && table.columns.length > 0 && (
                                        <div className="mt-2">
                                          <details className="text-xs">
                                            <summary className="cursor-pointer text-blue-600 dark:text-blue-400 hover:underline">
                                              View {table.columns.length} columns
                                            </summary>
                                            <div className="mt-2 ml-4 space-y-1">
                                              {table.columns.map((col: any, colIdx: number) => (
                                                <div key={colIdx} className="flex items-center gap-2">
                                                  <span className="font-mono">{col.name}</span>
                                                  <Badge variant="secondary" className="text-xs">
                                                    {col.type}
                                                  </Badge>
                                                </div>
                                              ))}
                                            </div>
                                          </details>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )})}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Notebooks */}
                      {discoveredLineage.workspace_info.notebooks && discoveredLineage.workspace_info.notebooks.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <FileText className="w-5 h-5" />
                              Notebooks ({discoveredLineage.workspace_info.notebooks.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              {discoveredLineage.workspace_info.notebooks.map((notebook: any, idx: number) => (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(notebook.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(notebook.guid);
                                        } else {
                                          newSet.delete(notebook.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="font-medium truncate">{notebook.name}</div>
                                      {showTechnicalDetails && (
                                        <>
                                          <div className="text-xs text-muted-foreground mt-1 truncate">
                                            GUID: {notebook.guid}
                                          </div>
                                          {notebook.qualified_name && (
                                            <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                              {notebook.qualified_name}
                                            </div>
                                          )}
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Warehouses */}
                      {discoveredLineage.workspace_info.warehouses && discoveredLineage.workspace_info.warehouses.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <Database className="w-5 h-5" />
                              Warehouses ({discoveredLineage.workspace_info.warehouses.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              {discoveredLineage.workspace_info.warehouses.map((warehouse: any, idx: number) => (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(warehouse.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(warehouse.guid);
                                        } else {
                                          newSet.delete(warehouse.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="font-medium truncate">{warehouse.name}</div>
                                      {showTechnicalDetails && (
                                        <>
                                          <div className="text-xs text-muted-foreground mt-1 truncate">
                                            GUID: {warehouse.guid}
                                          </div>
                                          {warehouse.qualified_name && (
                                            <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                              {warehouse.qualified_name}
                                            </div>
                                          )}
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Files */}
                      {discoveredLineage.workspace_info.files && discoveredLineage.workspace_info.files.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <FileText className="w-5 h-5" />
                              Files ({discoveredLineage.workspace_info.files.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2 max-h-96 overflow-y-auto">
                              {discoveredLineage.workspace_info.files.map((file: any, idx: number) => (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(file.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(file.guid);
                                        } else {
                                          newSet.delete(file.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="font-medium truncate">{file.name}</div>
                                      {showTechnicalDetails && (
                                        <>
                                          <div className="text-xs text-muted-foreground mt-1 truncate">
                                            GUID: {file.guid}
                                          </div>
                                          {file.qualified_name && (
                                            <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                              {file.qualified_name}
                                            </div>
                                          )}
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Dataflows */}
                      {discoveredLineage.workspace_info.dataflows && discoveredLineage.workspace_info.dataflows.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <FileText className="w-5 h-5" />
                              Dataflows ({discoveredLineage.workspace_info.dataflows.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              {discoveredLineage.workspace_info.dataflows.map((dataflow: any, idx: number) => (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(dataflow.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(dataflow.guid);
                                        } else {
                                          newSet.delete(dataflow.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="font-medium truncate">{dataflow.name}</div>
                                      <div className="text-xs text-muted-foreground mt-1 truncate">
                                        GUID: {dataflow.guid}
                                      </div>
                                      {dataflow.qualified_name && (
                                        <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                          {dataflow.qualified_name}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Pipelines */}
                      {discoveredLineage.workspace_info.pipelines && discoveredLineage.workspace_info.pipelines.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <FileText className="w-5 h-5" />
                              Pipelines ({discoveredLineage.workspace_info.pipelines.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2">
                              {discoveredLineage.workspace_info.pipelines.map((pipeline: any, idx: number) => (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(pipeline.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(pipeline.guid);
                                        } else {
                                          newSet.delete(pipeline.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="font-medium truncate">{pipeline.name}</div>
                                      <div className="text-xs text-muted-foreground mt-1 truncate">
                                        GUID: {pipeline.guid}
                                      </div>
                                      {pipeline.qualified_name && (
                                        <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                          {pipeline.qualified_name}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}

                      {/* Other Assets */}
                      {discoveredLineage.workspace_info.other_assets && discoveredLineage.workspace_info.other_assets.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <FileText className="w-5 h-5" />
                              Other Assets ({discoveredLineage.workspace_info.other_assets.length})
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-2 max-h-96 overflow-y-auto">
                              {discoveredLineage.workspace_info.other_assets.map((asset: any, idx: number) => (
                                <div key={idx} className="p-3 bg-secondary/20 rounded border">
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={selectedDescriptionAssets.has(asset.guid)}
                                      onCheckedChange={(checked) => {
                                        const newSet = new Set(selectedDescriptionAssets);
                                        if (checked) {
                                          newSet.add(asset.guid);
                                        } else {
                                          newSet.delete(asset.guid);
                                        }
                                        setSelectedDescriptionAssets(newSet);
                                      }}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-2">
                                        <div className="font-medium truncate">{asset.name}</div>
                                        {asset.entity_type && (
                                          <Badge variant="outline" className="text-xs">
                                            {asset.entity_type}
                                          </Badge>
                                        )}
                                      </div>
                                      <div className="text-xs text-muted-foreground mt-1 truncate">
                                        GUID: {asset.guid}
                                      </div>
                                      {asset.qualified_name && (
                                        <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                          {asset.qualified_name}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  )}

                  {/* Generate Descriptions Button */}
                  {discoveredLineage?.workspace_info && selectedDescriptionAssets.size > 0 && (
                    <div className="mt-6">
                      <Button
                        onClick={generateDescriptions}
                        disabled={isGeneratingDescription}
                        className="w-full"
                        size="lg"
                      >
                        {isGeneratingDescription ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Generating Descriptions...
                          </>
                        ) : (
                          <>
                            <FileText className="w-4 h-4 mr-2" />
                            Generate Descriptions ({selectedDescriptionAssets.size} selected)
                          </>
                        )}
                      </Button>
                    </div>
                  )}

                  {/* Description Results - Validation Panel */}
                  {descriptionResults.length > 0 && (
                    <Card className="mt-6 border-2 border-green-500">
                      <CardHeader>
                        <CardTitle className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <FileText className="w-5 h-5" />
                            Generated Descriptions - Review & Edit
                          </div>
                          <Badge variant="secondary">{descriptionResults.length} descriptions</Badge>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-4 max-h-96 overflow-y-auto">
                          {descriptionResults.map((result) => {
                            const plainTextDescription = editingDescriptions[result.guid] || '';
                            const hasContent = plainTextDescription.length > 0;
                            
                            return (
                              <div key={result.guid} className="p-4 border rounded-lg space-y-2">
                                <div className="flex items-center justify-between">
                                  <div className="font-semibold">{result.name}</div>
                                  <Badge variant="outline">{result.asset_type}</Badge>
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  GUID: {result.guid}
                                </div>
                                <div className="mt-2">
                                  <Label className="text-xs">Description (Plain Text):</Label>
                                  <textarea
                                    className={`w-full mt-1 p-3 text-sm border rounded font-sans resize-y ${hasContent ? 'min-h-[400px]' : 'min-h-[100px]'}`}
                                    value={plainTextDescription}
                                    onChange={(e) => {
                                      setEditingDescriptions({
                                        ...editingDescriptions,
                                        [result.guid]: e.target.value
                                      });
                                    }}
                                    placeholder="Description will appear here..."
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        <div className="flex gap-2 pt-4 border-t">
                          <Button
                            onClick={applyDescriptionsToPurview}
                            className="flex-1"
                            disabled={isApplyingDescriptions}
                          >
                            {isApplyingDescriptions ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Applying to Purview...
                              </>
                            ) : (
                              <>
                                <Check className="w-4 h-4 mr-2" />
                                Apply to Asset
                              </>
                            )}
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => {
                              setDescriptionResults([]);
                              setEditingDescriptions({});
                              setOriginalHtmlDescriptions({});
                            }}
                            disabled={isApplyingDescriptions}
                          >
                            Cancel
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </TabsContent>

              {/* Data Lineage Tab */}
              <TabsContent value="lineage" className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-start gap-2 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div className="space-y-2 flex-1">
                      <p className="text-sm text-blue-900 dark:text-blue-100 font-medium">
                        Automated Lineage Discovery for Fabric Assets
                      </p>
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        Select a Fabric workspace to automatically discover data lineage relationships using AI. 
                        The system will analyze upstream sources, downstream destinations, and transformation processes.
                      </p>
                    </div>
                  </div>

                  {/* Workspace Selection */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="workspace-select">Select Fabric Workspace</Label>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={fetchWorkspaces}
                        disabled={isLoadingWorkspaces}
                      >
                        <RefreshCw className={`w-3 h-3 ${isLoadingWorkspaces ? 'animate-spin' : ''}`} />
                      </Button>
                    </div>
                    <Select
                      value={selectedWorkspace}
                      onValueChange={setSelectedWorkspace}
                      disabled={isLoadingWorkspaces || isDiscoveringLineage}
                    >
                      <SelectTrigger id="workspace-select">
                        <SelectValue placeholder={isLoadingWorkspaces ? "Loading workspaces..." : "Choose a workspace"} />
                      </SelectTrigger>
                      <SelectContent>
                        {workspaces.map((workspace) => (
                          <SelectItem key={workspace.workspace_id} value={workspace.workspace_id}>
                            <div className="flex items-center justify-between w-full">
                              <span>{workspace.workspace_name}</span>
                              <Badge variant="secondary" className="ml-2">
                                {workspace.asset_count} assets
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      {workspaces.length} workspace(s) available with Fabric assets
                    </p>
                  </div>

                  {/* Discover Button */}
                  <Button
                    onClick={handleDiscoverLineage}
                    disabled={!selectedWorkspace || isDiscoveringLineage}
                    className="w-full"
                  >
                    {isDiscoveringLineage ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Discovering Lineage...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 mr-2" />
                        Discover Lineage with AI
                      </>
                    )}
                  </Button>

                  {/* Cleanup Button */}
                  <div className="space-y-4">
                    {/* Created Lineages Management */}
                    {createdLineages.length > 0 && (
                      <Card className="bg-muted/30">
                        <CardHeader>
                          <CardTitle className="text-base flex items-center gap-2">
                            <GitBranch className="w-4 h-4" />
                            Created Lineage Relationships ({createdLineages.length})
                          </CardTitle>
                          <CardDescription>
                            Manage lineages created in this session
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  const allIndices = new Set(createdLineages.map((_, idx) => idx));
                                  setSelectedLineageIndices(allIndices);
                                }}
                              >
                                Select All
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSelectedLineageIndices(new Set())}
                              >
                                Deselect All
                              </Button>
                              <span className="text-sm text-muted-foreground">
                                {selectedLineageIndices.size} selected
                              </span>
                            </div>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={handleDeleteSelectedLineages}
                              disabled={selectedLineageIndices.size === 0}
                            >
                              <Trash2 className="w-3 h-3 mr-1" />
                              Delete Selected
                            </Button>
                          </div>
                          <div className="space-y-2 max-h-64 overflow-y-auto">
                            {createdLineages.map((lineage, idx) => {
                              const isSelected = selectedLineageIndices.has(idx);
                              return (
                                <div
                                  key={idx}
                                  className={`p-3 bg-background rounded border transition-all ${ 
                                    isSelected ? 'border-primary ring-2 ring-primary/20' : 'border-border'
                                  }`}
                                >
                                  <div className="flex items-start gap-2">
                                    <Checkbox
                                      id={`lineage-${idx}`}
                                      checked={isSelected}
                                      onCheckedChange={(checked) => {
                                        const newSelection = new Set(selectedLineageIndices);
                                        if (checked) {
                                          newSelection.add(idx);
                                        } else {
                                          newSelection.delete(idx);
                                        }
                                        setSelectedLineageIndices(newSelection);
                                      }}
                                      className="mt-1"
                                    />
                                    <label htmlFor={`lineage-${idx}`} className="flex-1 cursor-pointer space-y-1">
                                      <div className="text-sm font-medium">{lineage.process_name}</div>
                                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                                        <span>{lineage.source_name}</span>
                                        <span>→</span>
                                        <span>{lineage.target_name}</span>
                                      </div>
                                      <div className="text-xs font-mono text-muted-foreground">
                                        {lineage.process_guid}
                                      </div>
                                    </label>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>

                  {/* Discovered Lineage Results */}
                  {discoveredLineage && (
                    <div className="space-y-4 p-4 bg-muted/50 rounded-lg border">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium flex items-center gap-2">
                          <GitBranch className="w-4 h-4" />
                          Discovered Lineage
                        </h3>
                        <Badge variant={discoveredLineage.mode === 'ai_discovered' ? 'default' : 'secondary'}>
                          {discoveredLineage.mode === 'ai_discovered' ? 'AI Discovered' : 'Purview Relationships'}
                        </Badge>
                      </div>

                      {/* Workspace Info */}
                      {discoveredLineage.workspace_info && (
                        <div className="text-sm space-y-1 p-3 bg-background rounded border">
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">Workspace:</span>
                            <span className="font-medium">{discoveredLineage.workspace_info.workspace_name}</span>
                          </div>
                        </div>
                      )}

                      {/* New Format: Lineage Mappings */}
                      {discoveredLineage.lineage?.lineage_mappings && discoveredLineage.lineage.lineage_mappings.length > 0 && (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <Label className="flex items-center gap-2">
                              <GitBranch className="w-4 h-4" />
                              Data Lineage Mappings ({discoveredLineage.lineage.lineage_mappings.length})
                            </Label>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  const allIndices = new Set(discoveredLineage.lineage.lineage_mappings.map((_: any, idx: number) => idx));
                                  setSelectedMappingIndices(allIndices);
                                }}
                              >
                                Select All
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSelectedMappingIndices(new Set())}
                              >
                                Deselect All
                              </Button>
                              <span className="text-sm text-muted-foreground">
                                {selectedMappingIndices.size} selected
                              </span>
                            </div>
                          </div>
                          <div className="space-y-3">
                            {discoveredLineage.lineage.lineage_mappings.map((mapping: any, idx: number) => {
                              const isSelected = selectedMappingIndices.has(idx);
                              return (
                              <div 
                                key={idx} 
                                className={`p-3 bg-background rounded border space-y-2 transition-all ${
                                  isSelected ? 'border-primary ring-2 ring-primary/20' : 'border-border'
                                }`}
                              >
                                <div className="flex items-center gap-2">
                                  <Checkbox
                                    id={`mapping-${idx}`}
                                    checked={isSelected}
                                    onCheckedChange={(checked) => {
                                      const newSelected = new Set(selectedMappingIndices);
                                      if (checked) {
                                        newSelected.add(idx);
                                      } else {
                                        newSelected.delete(idx);
                                      }
                                      setSelectedMappingIndices(newSelected);
                                    }}
                                  />
                                  <Label htmlFor={`mapping-${idx}`} className="flex items-center gap-2 cursor-pointer flex-1">
                                    <Badge variant="outline" className="text-xs">Mapping {idx + 1}</Badge>
                                    <span className="text-xs text-muted-foreground">{mapping.process_name}</span>
                                  </Label>
                                </div>
                                
                                {/* Source to Target Flow */}
                                <div className="flex items-center gap-2 text-sm">
                                  <div className="flex-1 p-2 bg-blue-50 dark:bg-blue-950/20 rounded border">
                                    <div className="font-medium">{mapping.source_table_name}</div>
                                    <div className="text-xs text-muted-foreground">Source</div>
                                    {mapping.source_table_qualified_name && extractContainerInfo(mapping.source_table_qualified_name) && (
                                      <div className="text-xs text-muted-foreground mt-1">
                                        <Badge variant="secondary" className="text-xs">
                                          {extractContainerInfo(mapping.source_table_qualified_name)?.type}: {extractContainerInfo(mapping.source_table_qualified_name)?.name}
                                        </Badge>
                                      </div>
                                    )}
                                  </div>
                                  <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                                  <div className="flex-1 p-2 bg-green-50 dark:bg-green-950/20 rounded border">
                                    <div className="font-medium">{mapping.target_table_name}</div>
                                    <div className="text-xs text-muted-foreground">Target</div>
                                    {mapping.target_table_qualified_name && extractContainerInfo(mapping.target_table_qualified_name) && (
                                      <div className="text-xs text-muted-foreground mt-1">
                                        <Badge variant="secondary" className="text-xs">
                                          {extractContainerInfo(mapping.target_table_qualified_name)?.type}: {extractContainerInfo(mapping.target_table_qualified_name)?.name}
                                        </Badge>
                                      </div>
                                    )}
                                  </div>
                                </div>

                                {/* Column Mappings */}
                                {mapping.column_mappings && mapping.column_mappings.length > 0 && (
                                  <div className="ml-4 space-y-2">
                                    <div className="flex items-center justify-between">
                                      <div className="text-xs font-medium text-muted-foreground">
                                        Column Mappings ({mapping.column_mappings.filter((cm: any) => cm.source_column && cm.target_column).length} mapped / {mapping.column_mappings.filter((cm: any) => cm.source_column).length} source columns):
                                      </div>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 text-xs"
                                        onClick={() => setEditingMappingIndex(editingMappingIndex === idx ? null : idx)}
                                      >
                                        {editingMappingIndex === idx ? (
                                          <><X className="w-3 h-3 mr-1" /> Cancel</>
                                        ) : (
                                          <><Edit className="w-3 h-3 mr-1" /> Edit Mappings</>
                                        )}
                                      </Button>
                                    </div>
                                    
                                    {/* Column Headers */}
                                    <div className="flex items-center gap-3 px-2 pb-1 border-b">
                                      <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 flex-1">Source</div>
                                      <div className="w-6 flex-shrink-0"></div>
                                      <div className="text-xs font-semibold text-green-600 dark:text-green-400 flex-1">Target</div>
                                    </div>
                                    
                                    {/* Column Mappings */}
                                    <div className="space-y-1.5 max-h-60 overflow-y-auto">
                                      {mapping.column_mappings
                                        .filter((colMap: any) => colMap.source_column && colMap.source_column.trim() !== '') // Only show mappings with source column
                                        .map((colMap: any, colIdx: number) => {
                                          // Find the original index for updating
                                          const originalIdx = mapping.column_mappings.findIndex(
                                            (cm: any) => cm.source_column === colMap.source_column && cm.target_column === colMap.target_column
                                          );
                                          return (
                                        <div key={colIdx} className="flex items-center gap-3 px-2">
                                          <div className="flex-1 min-w-0">
                                            <span className="font-mono text-xs text-blue-600 dark:text-blue-400 truncate block">{colMap.source_column}</span>
                                          </div>
                                          <div className="w-6 flex-shrink-0 flex justify-center">
                                            <ArrowRight className="w-4 h-4 text-muted-foreground" />
                                          </div>
                                          <div className="flex-1 min-w-0">
                                            {editingMappingIndex === idx ? (
                                              <select
                                                className="flex h-7 w-full rounded-md border border-input bg-background px-2 py-1 text-xs ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring font-mono"
                                                value={colMap.target_column || ""}
                                                onChange={(e) => handleUpdateColumnMapping(idx, originalIdx, e.target.value)}
                                              >
                                                <option value="">(not mapped)</option>
                                                {mapping.target_columns?.map((targetCol: any) => (
                                                  <option key={targetCol.name} value={targetCol.name}>
                                                    {targetCol.name}
                                                  </option>
                                                ))}
                                              </select>
                                            ) : (
                                              colMap.target_column ? (
                                                <span className="font-mono text-xs text-green-600 dark:text-green-400 truncate block">{colMap.target_column}</span>
                                              ) : (
                                                <span className="font-mono text-xs text-muted-foreground italic">(not mapped)</span>
                                              )
                                            )}
                                          </div>
                                        </div>
                                        );
                                      })}
                                    </div>
                                    
                                    {/* Unmapped Target Columns Section */}
                                    {(() => {
                                      // Find all target columns that are NOT mapped from any source
                                      const mappedTargetNames = new Set(
                                        mapping.column_mappings
                                          .filter((cm: any) => cm.source_column && cm.source_column.trim() !== '' && cm.target_column)
                                          .map((cm: any) => cm.target_column.toLowerCase())
                                      );
                                      const unmappedTargets = (mapping.target_columns || []).filter(
                                        (col: any) => !mappedTargetNames.has(col.name.toLowerCase())
                                      );
                                      
                                      if (unmappedTargets.length === 0) return null;
                                      
                                      return (
                                        <div className="mt-4 pt-3 border-t">
                                          <div className="text-xs font-medium text-muted-foreground mb-2">
                                            Unmapped Target Columns ({unmappedTargets.length}):
                                          </div>
                                          <div className="space-y-1.5">
                                            {unmappedTargets.map((col: any, colIdx: number) => (
                                              <div key={`unmapped-${colIdx}`} className="flex items-center gap-3 px-2">
                                                <div className="flex-1 min-w-0">
                                                  <span className="font-mono text-xs text-muted-foreground italic">No source</span>
                                                </div>
                                                <div className="w-6 flex-shrink-0 flex justify-center">
                                                  <ArrowRight className="w-4 h-4 text-muted-foreground opacity-50" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                  <span className="font-mono text-xs text-green-600 dark:text-green-400 truncate block">{col.name}</span>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      );
                                    })()}
                                  </div>
                                )}

                                {/* Process Information */}
                                {mapping.process_type && (
                                  <div className="text-xs text-muted-foreground">
                                    Process Type: <Badge variant="secondary" className="text-xs">{mapping.process_type}</Badge>
                                  </div>
                                )}
                              </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Upstream Assets */}
                      {discoveredLineage.lineage?.upstream_assets && discoveredLineage.lineage.upstream_assets.length > 0 && (
                        <div className="space-y-2">
                          <Label className="flex items-center gap-2">
                            <ArrowRight className="w-4 h-4 rotate-180" />
                            Upstream Sources ({discoveredLineage.lineage.upstream_assets.length})
                          </Label>
                          <div className="space-y-1">
                            {discoveredLineage.lineage.upstream_assets.map((asset: any, idx: number) => (
                              <div key={idx} className="p-2 bg-background rounded border text-sm">
                                <div className="font-medium">{asset.name}</div>
                                <div className="text-xs text-muted-foreground">{asset.type}</div>
                                {asset.qualified_name && (
                                  <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                    {asset.qualified_name}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Downstream Assets */}
                      {discoveredLineage.lineage?.downstream_assets && discoveredLineage.lineage.downstream_assets.length > 0 && (
                        <div className="space-y-2">
                          <Label className="flex items-center gap-2">
                            <ArrowRight className="w-4 h-4" />
                            Downstream Destinations ({discoveredLineage.lineage.downstream_assets.length})
                          </Label>
                          <div className="space-y-1">
                            {discoveredLineage.lineage.downstream_assets.map((asset: any, idx: number) => (
                              <div key={idx} className="p-2 bg-background rounded border text-sm">
                                <div className="font-medium">{asset.name}</div>
                                <div className="text-xs text-muted-foreground">{asset.type}</div>
                                {asset.qualified_name && (
                                  <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                    {asset.qualified_name}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Processes */}
                      {discoveredLineage.lineage?.processes && discoveredLineage.lineage.processes.length > 0 && (
                        <div className="space-y-2">
                          <Label className="flex items-center gap-2">
                            <GitBranch className="w-4 h-4" />
                            Transformation Processes ({discoveredLineage.lineage.processes.length})
                          </Label>
                          <div className="space-y-1">
                            {discoveredLineage.lineage.processes.map((process: any, idx: number) => (
                              <div key={idx} className="p-2 bg-background rounded border text-sm">
                                <div className="font-medium">{process.name}</div>
                                <div className="text-xs text-muted-foreground">{process.type}</div>
                                {process.qualified_name && (
                                  <div className="text-xs text-muted-foreground font-mono mt-1 truncate">
                                    {process.qualified_name}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* No lineage found */}
                      {(!discoveredLineage.lineage?.lineage_mappings || discoveredLineage.lineage.lineage_mappings.length === 0) &&
                       (!discoveredLineage.lineage?.upstream_assets || discoveredLineage.lineage.upstream_assets.length === 0) &&
                       (!discoveredLineage.lineage?.downstream_assets || discoveredLineage.lineage.downstream_assets.length === 0) &&
                       (!discoveredLineage.lineage?.processes || discoveredLineage.lineage.processes.length === 0) && (
                        <div className="text-sm text-muted-foreground text-center py-4">
                          No lineage relationships discovered for this workspace
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex gap-2 pt-2">
                        <Button
                          onClick={handleCreateLineage}
                          disabled={
                            isCreatingLineage ||
                            selectedMappingIndices.size === 0 ||
                            (!discoveredLineage.lineage?.lineage_mappings || discoveredLineage.lineage.lineage_mappings.length === 0) &&
                            (!discoveredLineage.lineage?.upstream_assets || discoveredLineage.lineage.upstream_assets.length === 0) &&
                            (!discoveredLineage.lineage?.downstream_assets || discoveredLineage.lineage.downstream_assets.length === 0)
                          }
                          className="flex-1"
                        >
                          {isCreatingLineage ? (
                            <>
                              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                              Creating Lineage...
                            </>
                          ) : (
                            <>
                              <CheckCircle2 className="w-4 h-4 mr-2" />
                              Approve & Create Lineage
                            </>
                          )}
                        </Button>
                        <Button
                          onClick={async () => {
                            // Delete ALL lineage for this workspace from Purview
                            if (!selectedWorkspace) {
                              toast({
                                title: "No Workspace Selected",
                                description: "Please select a workspace first",
                                variant: "destructive",
                              });
                              return;
                            }
                            
                            const workspace = workspaces.find(w => w.workspace_id === selectedWorkspace);
                            const workspaceName = workspace?.workspace_name || selectedWorkspace;
                            
                            if (!confirm(`Delete ALL lineage relationships for workspace "${workspaceName}"? This will remove all lineage processes from Purview for this workspace.`)) {
                              return;
                            }
                            
                            try {
                              toast({
                                title: "⏳ Deleting Workspace Lineage",
                                description: `Deleting all lineage for "${workspaceName}"...`,
                                duration: 5000,
                              });

                              const response = await fetch("http://localhost:8000/api/lineage/delete", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                  workspace_id: selectedWorkspace,
                                }),
                              });

                              const data = await response.json();

                              if (response.ok && data.success) {
                                toast({
                                  title: " Lineage Deleted",
                                  description: data.message || "All lineage relationships deleted from Purview",
                                  duration: 5000,
                                });
                                
                                // Clear UI state after successful deletion
                                setDiscoveredLineage(null);
                                setLineageMappings([]);
                                setSelectedMappingIndices(new Set());
                              } else {
                                throw new Error(data.error || "Failed to delete lineage");
                              }
                            } catch (error) {
                              const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
                              toast({
                                title: " Deletion Error",
                                description: errorMessage,
                                variant: "destructive",
                                duration: 5000,
                              });
                            }
                          }}
                          variant="destructive"
                          className="flex-shrink-0"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete Workspace Lineage
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* AI Description Tab */}
              <TabsContent value="description" className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-start gap-2 p-4 bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800 rounded-lg">
                    <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
                    <div className="space-y-2 flex-1">
                      <p className="text-sm text-purple-900 dark:text-purple-100 font-medium">
                        AI-Generated Asset Descriptions
                      </p>
                      <p className="text-sm text-purple-700 dark:text-purple-300">
                        Generate detailed descriptions for selected assets using AI. The AI analyzes asset names, types, 
                        schemas, and relationships to create comprehensive documentation.
                      </p>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Business Glossary Sync Tab */}
              <TabsContent value="glossary" className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-start gap-2 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div className="space-y-2 flex-1">
                      <p className="text-sm text-blue-900 dark:text-blue-100 font-medium">
                        Business Glossary Sync
                      </p>
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        Sync governance domain terms from the Unified Catalog to the Classic Business Glossary. 
                        This creates one glossary per domain and adds all terms with their descriptions and contacts.
                      </p>
                    </div>
                  </div>

                  {/* Preview Section */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Preview Sync</CardTitle>
                      <CardDescription>
                        See what will be synced before making changes
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <Button
                        onClick={async () => {
                          setIsLoadingGlossaryPreview(true);
                          setGlossaryPreview(null);
                          try {
                            const response = await fetch('http://localhost:8000/api/glossary/preview');
                            const data = await response.json();
                            if (data.success) {
                              setGlossaryPreview(data.preview);
                              toast({
                                title: "Preview loaded",
                                description: `Found ${data.preview.domains_found} domains with ${data.preview.unified_catalog_terms_count} terms`,
                              });
                            } else {
                              throw new Error(data.error || 'Failed to load preview');
                            }
                          } catch (error: any) {
                            toast({
                              title: "Preview failed",
                              description: error.message,
                              variant: "destructive",
                            });
                          } finally {
                            setIsLoadingGlossaryPreview(false);
                          }
                        }}
                        disabled={isLoadingGlossaryPreview}
                      >
                        {isLoadingGlossaryPreview && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        <Eye className="w-4 h-4 mr-2" />
                        Load Preview
                      </Button>

                      {glossaryPreview && (
                        <div className="space-y-4">
                          <div className="grid grid-cols-3 gap-4">
                            <Card>
                              <CardContent className="pt-6">
                                <div className="text-2xl font-bold">{glossaryPreview.unified_catalog_terms_count}</div>
                                <p className="text-xs text-muted-foreground">Unified Catalog Terms</p>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardContent className="pt-6">
                                <div className="text-2xl font-bold">{glossaryPreview.classic_glossaries_count}</div>
                                <p className="text-xs text-muted-foreground">Existing Glossaries</p>
                              </CardContent>
                            </Card>
                            <Card>
                              <CardContent className="pt-6">
                                <div className="text-2xl font-bold">{glossaryPreview.domains_found}</div>
                                <p className="text-xs text-muted-foreground">Domains Found</p>
                              </CardContent>
                            </Card>
                          </div>

                          <div className="space-y-2">
                            <Label>Domains to Sync</Label>
                            <div className="max-h-96 overflow-y-auto space-y-2 border rounded-lg p-4">
                              {glossaryPreview.domains.map((domain: any, index: number) => (
                                <div key={index} className="p-3 bg-muted/50 rounded-md">
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium">{domain.domain_name}</span>
                                      <Badge variant={domain.glossary_exists ? "secondary" : "default"}>
                                        {domain.glossary_exists ? "Exists" : "New"}
                                      </Badge>
                                    </div>
                                    <span className="text-sm text-muted-foreground">
                                      {domain.terms_count} terms
                                    </span>
                                  </div>
                                  {domain.sample_terms && domain.sample_terms.length > 0 && (
                                    <div className="text-xs text-muted-foreground ml-4">
                                      Sample terms: {domain.sample_terms.map((t: any) => t.name).join(", ")}
                                      {domain.terms_count > domain.sample_terms.length && "..."}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Sync Section */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Run Sync</CardTitle>
                      <CardDescription>
                        Sync domains and terms to Classic Business Glossary
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <Alert>
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          Only new glossaries and terms will be created. Existing items will be preserved.
                        </AlertDescription>
                      </Alert>

                      <div className="flex gap-2">
                        <Button
                          onClick={async () => {
                            setIsSyncingGlossary(true);
                            setGlossarySyncResult(null);
                            try {
                              const response = await fetch('http://localhost:8000/api/glossary/sync', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ dry_run: true })
                              });
                              const data = await response.json();
                              if (data.success) {
                                setGlossarySyncResult(data);
                                toast({
                                  title: "Dry run completed",
                                  description: `Would create ${data.glossaries_created} glossaries and ${data.terms_created} terms`,
                                });
                              } else {
                                throw new Error(data.message || 'Dry run failed');
                              }
                            } catch (error: any) {
                              toast({
                                title: "Dry run failed",
                                description: error.message,
                                variant: "destructive",
                              });
                            } finally {
                              setIsSyncingGlossary(false);
                            }
                          }}
                          variant="outline"
                          disabled={isSyncingGlossary}
                        >
                          {isSyncingGlossary && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                          <Eye className="w-4 h-4 mr-2" />
                          Dry Run
                        </Button>

                        <Button
                          onClick={async () => {
                            setIsSyncingGlossary(true);
                            setGlossarySyncResult(null);
                            try {
                              const response = await fetch('http://localhost:8000/api/glossary/sync', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ dry_run: false })
                              });
                              const data = await response.json();
                              if (data.success) {
                                setGlossarySyncResult(data);
                                toast({
                                  title: "Sync completed successfully",
                                  description: `Created ${data.glossaries_created} glossaries and ${data.terms_created} terms`,
                                });
                              } else {
                                throw new Error(data.message || 'Sync failed');
                              }
                            } catch (error: any) {
                              toast({
                                title: "Sync failed",
                                description: error.message,
                                variant: "destructive",
                              });
                            } finally {
                              setIsSyncingGlossary(false);
                            }
                          }}
                          disabled={isSyncingGlossary}
                        >
                          {isSyncingGlossary && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Sync Now
                        </Button>
                      </div>

                      {glossarySyncResult && (
                        <Alert variant={glossarySyncResult.success ? "default" : "destructive"}>
                          {glossarySyncResult.success ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                          <AlertDescription>
                            <div className="space-y-2">
                              <p className="font-medium">{glossarySyncResult.message}</p>
                              <div className="text-sm space-y-1">
                                <p>• Unified Catalog Terms: {glossarySyncResult.unified_terms_count}</p>
                                <p>• Domains Processed: {glossarySyncResult.domains_processed}</p>
                                <p>• Glossaries Created: {glossarySyncResult.glossaries_created}</p>
                                <p>• Glossaries Skipped: {glossarySyncResult.glossaries_skipped}</p>
                                <p>• Terms Created: {glossarySyncResult.terms_created}</p>
                                <p>• Terms Skipped: {glossarySyncResult.terms_skipped}</p>
                              </div>
                              {glossarySyncResult.errors && glossarySyncResult.errors.length > 0 && (
                                <div className="text-sm mt-2">
                                  <p className="font-medium">Errors:</p>
                                  <ul className="list-disc list-inside">
                                    {glossarySyncResult.errors.map((error: string, idx: number) => (
                                      <li key={idx}>{error}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </AlertDescription>
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
