import { describe, it, expect, beforeEach } from 'vitest';
import { useUserStore } from '../store';

describe('useUserStore', () => {
  beforeEach(() => {
    useUserStore.getState().clearAuth();
  });

  it('has null initial state', () => {
    const state = useUserStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.refreshToken).toBeNull();
  });

  it('setAuth sets user, token, and refreshToken', () => {
    useUserStore.getState().setAuth({
      user: {
        id: 'u1',
        first_name: 'Иван',
        onboarding_complete: false,
        subscription_status: 'free',
      },
      token: 'access-token',
      refreshToken: 'refresh-token',
    });

    const state = useUserStore.getState();
    expect(state.user?.id).toBe('u1');
    expect(state.user?.first_name).toBe('Иван');
    expect(state.token).toBe('access-token');
    expect(state.refreshToken).toBe('refresh-token');
  });

  it('setAuth without refreshToken defaults to null', () => {
    useUserStore.getState().setAuth({
      user: {
        id: 'u2',
        first_name: 'Test',
        onboarding_complete: true,
        subscription_status: 'premium',
      },
      token: 'tok',
    });

    expect(useUserStore.getState().refreshToken).toBeNull();
  });

  it('clearAuth resets all fields to null', () => {
    useUserStore.getState().setAuth({
      user: {
        id: 'u1',
        first_name: 'Test',
        onboarding_complete: false,
        subscription_status: 'free',
      },
      token: 'tok',
      refreshToken: 'ref',
    });

    useUserStore.getState().clearAuth();

    const state = useUserStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.refreshToken).toBeNull();
  });

  it('updateUser merges partial into existing user', () => {
    useUserStore.getState().setAuth({
      user: {
        id: 'u1',
        first_name: 'Test',
        onboarding_complete: false,
        subscription_status: 'free',
      },
      token: 'tok',
    });

    useUserStore.getState().updateUser({ onboarding_complete: true });

    const user = useUserStore.getState().user;
    expect(user?.onboarding_complete).toBe(true);
    expect(user?.first_name).toBe('Test');
  });

  it('updateUser does nothing when user is null', () => {
    useUserStore.getState().updateUser({ onboarding_complete: true });
    expect(useUserStore.getState().user).toBeNull();
  });
});
