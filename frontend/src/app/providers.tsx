import React from 'react';

/**
 * Global context providers wrapper.
 *
 * Currently passes children through directly.
 * Add providers here as the app grows (e.g., QueryClientProvider, ThemeProvider).
 */
interface ProvidersProps {
  children: React.ReactNode;
}

export const Providers: React.FC<ProvidersProps> = ({ children }) => {
  return <>{children}</>;
};
