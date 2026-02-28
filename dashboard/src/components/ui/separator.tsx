// Separator primitive — wraps Radix UI Separator for horizontal/vertical dividers
import * as SeparatorPrimitive from '@radix-ui/react-separator'
import { cn } from '../../lib/utils'

interface SeparatorProps extends React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root> {}

export function Separator({ className, orientation = 'horizontal', decorative = true, ...props }: SeparatorProps) {
  return (
    <SeparatorPrimitive.Root
      decorative={decorative}
      orientation={orientation}
      className={cn(
        'shrink-0 bg-border',
        orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
        className,
      )}
      {...props}
    />
  )
}
