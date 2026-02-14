/**
 * API Service for Purview Data Catalog
 * Handles all communication with the Flask backend
 */

import type { 
  PurviewAsset, 
  AssetStats, 
  ApiResponse, 
  HealthResponse 
} from '@/types/purview';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class PurviewApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Generic fetch wrapper with error handling
   */
  private async fetchApi<T>(
    endpoint: string, 
    options?: RequestInit
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`Error fetching ${endpoint}:`, error);
      throw error;
    }
  }

  /**
   * Check API health status
   */
  async healthCheck(): Promise<HealthResponse> {
    const response = await this.fetchApi<HealthResponse>('/api/health');
    return response.data;
  }

  /**
   * Get all assets from Purview
   */
  async getAssets(): Promise<{ assets: PurviewAsset[], unmappedCollections: string[] }> {
    const response = await this.fetchApi<PurviewAsset[]>('/api/assets');
    return {
      assets: response.data,
      unmappedCollections: (response as any).unmappedCollections || []
    };
  }

  /**
   * Get catalog statistics
   */
  async getStats(): Promise<AssetStats> {
    const response = await this.fetchApi<AssetStats>('/api/stats');
    return response.data;
  }

  /**
   * Get all data products from Purview
   */
  async getDataProducts(): Promise<any[]> {
    const response = await this.fetchApi<any[]>('/api/data-products');
    return response.data;
  }

  /**
   * Refresh data from Purview
   */
  async refreshData(): Promise<{ message: string; count: number }> {
    const response = await this.fetchApi<{ message: string; count: number }>(
      '/api/refresh',
      { method: 'POST' }
    );
    return response.data;
  }
}

// Export singleton instance
export const purviewApi = new PurviewApiService();

// Export class for testing
export default PurviewApiService;
