// Tooltip primitive — wraps Radix UI Tooltip with styled content
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { cn } from '../../lib/utils'

export const TooltipProvider = TooltipPrimitive.Provider
export const TooltipRoot = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  className,
  sideOffset = 4,
  ...props
}: React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'z-50 overflow-hidden rounded-md border border-border bg-popover px-3 py-1.5',
          'text-xs text-popover-foreground shadow-md',
          'animate-in fade-in-0 zoom-in-95',
          'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  )
}

/** Convenience wrapper: <Tooltip content="..."><child/></Tooltip> */
export function Tooltip({
  content,
  children,
  delayDuration = 300,
}: {
  content: React.ReactNode
  children: React.ReactNode
  delayDuration?: number
}) {
  return (
    <TooltipProvider>
      <TooltipRoot delayDuration={delayDuration}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent>{content}</TooltipContent>
      </TooltipRoot>
    </TooltipProvider>
  )
}
