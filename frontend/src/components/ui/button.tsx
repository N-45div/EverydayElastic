import * as React from "react"
import { cn } from "@/lib/utils"

type Variant = "default" | "secondary" | "outline" | "ghost" | "link"
type Size = "default" | "sm" | "lg" | "icon"

const baseStyles =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-60"

const variantStyles: Record<Variant, string> = {
  default: "bg-emerald-500 text-slate-950 hover:bg-emerald-400",
  secondary: "bg-slate-900 text-slate-100 border border-slate-700 hover:bg-slate-800",
  outline: "border border-slate-800 bg-transparent hover:bg-slate-900/60 text-slate-100",
  ghost: "text-slate-300 hover:bg-slate-800",
  link: "text-emerald-400 underline-offset-4 hover:underline",
}

const sizeStyles: Record<Size, string> = {
  default: "h-10 px-5 py-2",
  sm: "h-9 px-3",
  lg: "h-12 px-6 text-base",
  icon: "h-10 w-10",
}

export interface ButtonProps {
  asChild?: boolean
  variant?: Variant
  size?: Size
  className?: string
  type?: "button" | "submit" | "reset"
  children?: React.ReactNode
  onClick?: React.MouseEventHandler<HTMLElement>
  disabled?: boolean
}

export const buttonClasses = (
  variant: Variant = "default",
  size: Size = "default",
  className?: string
) => cn(baseStyles, variantStyles[variant], sizeStyles[size], className)

export function Button({
  asChild = false,
  variant = "default",
  size = "default",
  className,
  type = "button",
  children,
  ...rest
}: ButtonProps) {
  const classes = buttonClasses(variant, size, className)

  if (asChild) {
    return <span className={classes} {...rest}>{children}</span>
  }

  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  )
}

Button.displayName = "Button"
