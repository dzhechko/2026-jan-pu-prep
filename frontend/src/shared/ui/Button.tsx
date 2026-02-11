import React from 'react';
import { Spinner } from './Spinner';

type ButtonVariant = 'primary' | 'secondary' | 'danger';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  fullWidth?: boolean;
  children: React.ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-tg-button text-tg-button-text hover:opacity-90 active:opacity-80',
  secondary:
    'bg-tg-secondary-bg text-tg-text hover:opacity-90 active:opacity-80 border border-tg-hint/20',
  danger:
    'bg-tg-destructive text-white hover:opacity-90 active:opacity-80',
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  loading = false,
  fullWidth = false,
  disabled,
  children,
  className = '',
  ...props
}) => {
  const isDisabled = disabled || loading;

  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2
        rounded-xl px-6 py-3
        text-sm font-semibold
        transition-all duration-150 ease-in-out
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `.trim()}
      disabled={isDisabled}
      {...props}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
};
