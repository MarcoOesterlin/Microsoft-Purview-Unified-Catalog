/**
 * Type definitions for Purview Data Catalog API
 */

export interface PurviewAsset {
  id: string;
  name: string;
  assetType?: string;
  entityType?: string;
  contact?: string;
  tag?: string | string[];
  classification?: string | string[];
  description?: string;
  qualifiedName?: string;
  createTime?: string;
  updateTime?: string;
  owner?: string;
  expert?: string;
  [key: string]: any; // Allow additional dynamic properties from Purview
}

export interface AssetStats {
  totalAssets: number;
  assetTypes: Record<string, number>;
  entityTypes: Record<string, number>;
  withTags: number;
  withClassification: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  count?: number;
  message?: string;
}

export interface HealthResponse {
  success: boolean;
  status: string;
  message: string;
}

// Asset type status for UI
export type AssetStatus = 'verified' | 'pending' | 'draft';

// Asset type for UI display
export type AssetType = 'table' | 'view' | 'dataset' | 'database' | 'file' | 'notebook';

// Data product status
export type DataProductStatus = 'active' | 'draft' | 'archived';
