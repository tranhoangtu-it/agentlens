// Input primitive — styled text input with focus ring using CSS variables
import { forwardRef } from 'react'
import { cn } from '../../lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm',
        'text-foreground placeholder:text-muted-foreground',
        'transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'
