import { cn } from "@/lib/utils";

const variants = {
  default: "bg-background-2 text-text-2",
  success: "bg-success-light text-success",
  warning: "bg-[color:var(--warning)]/10 text-warning",
  danger: "bg-[color:var(--danger)]/10 text-danger",
  navy: "bg-navy-light text-navy",
  outline: "border border-border bg-transparent text-text-2",
} as const;

const sizes = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-xs",
} as const;

export interface BadgeProps {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  className?: string;
  children: React.ReactNode;
}

function Badge({
  variant = "default",
  size = "sm",
  className,
  children,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {children}
    </span>
  );
}

export { Badge };
