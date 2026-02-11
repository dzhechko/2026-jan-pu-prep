import React from 'react';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses: Record<string, string> = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-3',
  lg: 'h-12 w-12 border-4',
};

export const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className = '' }) => {
  return (
    <div
      className={`
        inline-block
        animate-spin
        rounded-full
        border-solid
        border-tg-button
        border-r-transparent
        ${sizeClasses[size]}
        ${className}
      `.trim()}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};
