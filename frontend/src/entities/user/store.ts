import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: number;
  telegramId: number;
  firstName: string;
  lastName?: string;
  username?: string;
  photoUrl?: string;
  languageCode?: string;
  isPremium?: boolean;
  onboardingCompleted?: boolean;
  subscriptionTier?: 'free' | 'premium';
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;

  setAuth: (payload: { user: User; token: string; refreshToken?: string }) => void;
  clearAuth: () => void;
  updateUser: (partial: Partial<User>) => void;
}

export const useUserStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      refreshToken: null,

      setAuth: ({ user, token, refreshToken }) =>
        set({
          user,
          token,
          refreshToken: refreshToken ?? null,
        }),

      clearAuth: () =>
        set({
          user: null,
          token: null,
          refreshToken: null,
        }),

      updateUser: (partial) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...partial } : null,
        })),
    }),
    {
      name: 'nutrimind-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
    },
  ),
);
