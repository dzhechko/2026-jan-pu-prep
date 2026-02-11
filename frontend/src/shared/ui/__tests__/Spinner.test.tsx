import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test-utils';
import { Spinner } from '../Spinner';

describe('Spinner', () => {
  it('renders with role="status"', () => {
    render(<Spinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('has aria-label "Loading"', () => {
    render(<Spinner />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading');
  });

  it('applies md size by default', () => {
    render(<Spinner />);
    const el = screen.getByRole('status');
    expect(el.className).toContain('h-8');
    expect(el.className).toContain('w-8');
  });

  it('applies sm size', () => {
    render(<Spinner size="sm" />);
    const el = screen.getByRole('status');
    expect(el.className).toContain('h-4');
    expect(el.className).toContain('w-4');
  });

  it('applies lg size', () => {
    render(<Spinner size="lg" />);
    const el = screen.getByRole('status');
    expect(el.className).toContain('h-12');
    expect(el.className).toContain('w-12');
  });

  it('includes spin animation class', () => {
    render(<Spinner />);
    expect(screen.getByRole('status').className).toContain('animate-spin');
  });

  it('applies custom className', () => {
    render(<Spinner className="my-spinner" />);
    expect(screen.getByRole('status').className).toContain('my-spinner');
  });

  it('contains sr-only text', () => {
    render(<Spinner />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
