import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const paddingClasses: Record<string, string> = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  onClick,
  padding = 'md',
}) => {
  const Component = onClick ? 'button' : 'div';

  return (
    <Component
      className={`
        bg-tg-section-bg
        rounded-2xl
        shadow-sm
        ${paddingClasses[padding]}
        ${onClick ? 'cursor-pointer active:scale-[0.98] transition-transform duration-100 w-full text-left' : ''}
        ${className}
      `.trim()}
      onClick={onClick}
    >
      {children}
    </Component>
  );
};
