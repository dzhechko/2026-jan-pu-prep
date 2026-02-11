import React from 'react';

const DashboardPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-tg-bg p-4">
      <h1 className="text-2xl font-bold text-tg-text">Dashboard</h1>
      <p className="mt-2 text-tg-hint">Your daily nutrition overview will appear here.</p>
    </div>
  );
};

export default DashboardPage;
