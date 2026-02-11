import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@/test-utils';
import { Card } from '../Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('renders as div when no onClick', () => {
    const { container } = render(<Card>Content</Card>);
    const card = container.firstElementChild;
    expect(card?.tagName).toBe('DIV');
  });

  it('renders as button when onClick is provided', () => {
    render(<Card onClick={() => {}}>Clickable</Card>);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick}>Click me</Card>);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('applies default md padding', () => {
    const { container } = render(<Card>Content</Card>);
    const card = container.firstElementChild;
    expect(card?.className).toContain('p-4');
  });

  it('applies sm padding', () => {
    const { container } = render(<Card padding="sm">Content</Card>);
    const card = container.firstElementChild;
    expect(card?.className).toContain('p-3');
  });

  it('applies lg padding', () => {
    const { container } = render(<Card padding="lg">Content</Card>);
    const card = container.firstElementChild;
    expect(card?.className).toContain('p-6');
  });

  it('applies no padding', () => {
    const { container } = render(<Card padding="none">Content</Card>);
    const card = container.firstElementChild;
    expect(card?.className).not.toContain('p-3');
    expect(card?.className).not.toContain('p-4');
    expect(card?.className).not.toContain('p-6');
  });

  it('applies custom className', () => {
    const { container } = render(<Card className="my-custom">Content</Card>);
    const card = container.firstElementChild;
    expect(card?.className).toContain('my-custom');
  });
});
