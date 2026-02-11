import React from 'react';

const PaywallPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-tg-bg p-4">
      <h1 className="text-2xl font-bold text-tg-text">Paywall</h1>
      <p className="mt-2 text-tg-hint">Upgrade to premium for full access.</p>
    </div>
  );
};

export default PaywallPage;
