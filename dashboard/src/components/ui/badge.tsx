// Badge primitive — variants: default, secondary, destructive, outline + status variants
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default:     'border-transparent bg-primary text-primary-foreground',
        secondary:   'border-transparent bg-secondary text-secondary-foreground',
        destructive: 'border-transparent bg-destructive/20 text-red-400 border-destructive/40',
        outline:     'border-border text-foreground',
        // Trace status variants
        completed:   'bg-green-500/20 text-green-400 border-green-500/40',
        running:     'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
        error:       'bg-red-500/20 text-red-400 border-red-500/40',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { badgeVariants }
