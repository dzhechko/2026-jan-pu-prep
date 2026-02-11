import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { MemoryRouter, MemoryRouterProps } from 'react-router-dom';

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  routerProps?: MemoryRouterProps;
}

function AllProviders({
  children,
  routerProps,
}: {
  children: React.ReactNode;
  routerProps?: MemoryRouterProps;
}) {
  return <MemoryRouter {...routerProps}>{children}</MemoryRouter>;
}

function customRender(
  ui: React.ReactElement,
  options?: CustomRenderOptions,
) {
  const { routerProps, ...renderOptions } = options ?? {};

  return render(ui, {
    wrapper: ({ children }) => (
      <AllProviders routerProps={routerProps}>{children}</AllProviders>
    ),
    ...renderOptions,
  });
}

export { customRender as render };
export { screen, waitFor, fireEvent, act } from '@testing-library/react';
