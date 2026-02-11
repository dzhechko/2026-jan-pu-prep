import { useCallback, useMemo } from 'react';
import { apiClient } from '@/shared/api/client';
import { useUserStore, User } from '@/entities/user/store';

interface LoginResponse {
  token: string;
  refresh_token: string;
  user: User;
}

interface UseAuthReturn {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (initData: string) => Promise<void>;
  logout: () => void;
}

export function useAuth(): UseAuthReturn {
  const user = useUserStore((state) => state.user);
  const token = useUserStore((state) => state.token);
  const setAuth = useUserStore((state) => state.setAuth);
  const clearAuth = useUserStore((state) => state.clearAuth);

  const isAuthenticated = useMemo(() => !!token && !!user, [token, user]);

  const login = useCallback(
    async (initData: string): Promise<void> => {
      const response = await apiClient.post<LoginResponse>('/auth/telegram', {
        init_data: initData,
      });

      const { user: userData, token: jwt, refresh_token } = response.data;

      setAuth({
        user: userData,
        token: jwt,
        refreshToken: refresh_token,
      });
    },
    [setAuth],
  );

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  return {
    user,
    token,
    isAuthenticated,
    login,
    logout,
  };
}
