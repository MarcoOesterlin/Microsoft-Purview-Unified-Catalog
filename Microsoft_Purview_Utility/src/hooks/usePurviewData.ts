/**
 * Custom React hooks for Purview data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { purviewApi } from '@/services/purviewApi';
import type { PurviewAsset, AssetStats } from '@/types/purview';

/**
 * Hook to fetch all Purview assets
 */
export function usePurviewAssets() {
  return useQuery<{ assets: PurviewAsset[], unmappedCollections: string[] }, Error>({
    queryKey: ['purview-assets'],
    queryFn: () => purviewApi.getAssets(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to fetch all data products
 */
export function usePurviewDataProducts() {
  return useQuery<any[], Error>({
    queryKey: ['purview-data-products'],
    queryFn: () => purviewApi.getDataProducts(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to fetch catalog statistics
 */
export function usePurviewStats() {
  return useQuery<AssetStats, Error>({
    queryKey: ['purview-stats'],
    queryFn: () => purviewApi.getStats(),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to check API health
 */
export function useApiHealth() {
  return useQuery({
    queryKey: ['api-health'],
    queryFn: () => purviewApi.healthCheck(),
    refetchInterval: 30000, // Check every 30 seconds
    retry: 3,
  });
}

/**
 * Hook to refresh Purview data
 */
export function useRefreshPurviewData() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => purviewApi.refreshData(),
    onSuccess: () => {
      // Invalidate and refetch all queries
      queryClient.invalidateQueries({ queryKey: ['purview-assets'] });
      queryClient.invalidateQueries({ queryKey: ['purview-data-products'] });
      queryClient.invalidateQueries({ queryKey: ['purview-stats'] });
    },
  });
}
