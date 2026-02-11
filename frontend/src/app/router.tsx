import { createHashRouter } from 'react-router-dom';
import React, { lazy, Suspense } from 'react';
import { Spinner } from '@/shared/ui';

const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage'));
const OnboardingPage = lazy(() => import('@/features/onboarding/OnboardingPage'));
const FoodLogPage = lazy(() => import('@/features/food-log/FoodLogPage'));
const InsightsPage = lazy(() => import('@/features/insights/InsightsPage'));
const LessonsPage = lazy(() => import('@/features/lessons/LessonsPage'));
const LessonDetailPage = lazy(() => import('@/features/lessons/LessonDetailPage'));
const PaywallPage = lazy(() => import('@/features/paywall/PaywallPage'));
const InvitePage = lazy(() => import('@/features/invite/InvitePage'));
const ProfilePage = lazy(() => import('@/features/profile/ProfilePage'));

const PageLoader: React.FC = () => (
  <div className="flex h-screen w-full items-center justify-center bg-tg-bg">
    <Spinner size="lg" />
  </div>
);

function withSuspense(Component: React.LazyExoticComponent<React.ComponentType>) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createHashRouter([
  {
    path: '/',
    element: withSuspense(DashboardPage),
  },
  {
    path: '/onboarding',
    element: withSuspense(OnboardingPage),
  },
  {
    path: '/food-log',
    element: withSuspense(FoodLogPage),
  },
  {
    path: '/insights',
    element: withSuspense(InsightsPage),
  },
  {
    path: '/lessons',
    element: withSuspense(LessonsPage),
  },
  {
    path: '/lessons/:id',
    element: withSuspense(LessonDetailPage),
  },
  {
    path: '/paywall',
    element: withSuspense(PaywallPage),
  },
  {
    path: '/invite',
    element: withSuspense(InvitePage),
  },
  {
    path: '/profile',
    element: withSuspense(ProfilePage),
  },
]);
