import { create } from "zustand";

interface AppState {
  currentJobId: string | null;
  setJobId: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentJobId: null,
  setJobId: (id) => set({ currentJobId: id }),
}));
