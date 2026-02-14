import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface SelectedAsset {
  id: string; // This is the GUID required by Purview API operations (add_owner, add_tag, add_classification, etc.)
  name: string;
  type: string;
  qualifiedName?: string;
}

interface SelectedAssetsContextType {
  selectedAssets: SelectedAsset[];
  addAsset: (asset: SelectedAsset) => void;
  removeAsset: (id: string) => void;
  clearAll: () => void;
  isSelected: (id: string) => boolean;
  getGuids: () => string[]; // Helper to get just the GUIDs for API operations
}

const SelectedAssetsContext = createContext<SelectedAssetsContextType | undefined>(undefined);

export function SelectedAssetsProvider({ children }: { children: ReactNode }) {
  const [selectedAssets, setSelectedAssets] = useState<SelectedAsset[]>(() => {
    // Load from localStorage on mount
    const stored = localStorage.getItem('selectedAssets');
    return stored ? JSON.parse(stored) : [];
  });

  // Persist to localStorage whenever selections change
  useEffect(() => {
    localStorage.setItem('selectedAssets', JSON.stringify(selectedAssets));
  }, [selectedAssets]);

  const addAsset = (asset: SelectedAsset) => {
    setSelectedAssets(prev => {
      // Avoid duplicates
      if (prev.some(a => a.id === asset.id)) return prev;
      return [...prev, asset];
    });
  };

  const removeAsset = (id: string) => {
    setSelectedAssets(prev => prev.filter(a => a.id !== id));
  };

  const clearAll = () => {
    setSelectedAssets([]);
  };

  const isSelected = (id: string) => {
    return selectedAssets.some(a => a.id === id);
  };

  const getGuids = () => {
    return selectedAssets.map(a => a.id);
  };

  return (
    <SelectedAssetsContext.Provider value={{ selectedAssets, addAsset, removeAsset, clearAll, isSelected, getGuids }}>
      {children}
    </SelectedAssetsContext.Provider>
  );
}

export function useSelectedAssets() {
  const context = useContext(SelectedAssetsContext);
  if (!context) {
    throw new Error('useSelectedAssets must be used within SelectedAssetsProvider');
  }
  return context;
}
