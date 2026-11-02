import type { ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

const buttonVariants = cva("button", {
  variants: {
    variant: { default: "button-primary", outline: "button-outline" },
  },
  defaultVariants: { variant: "default" },
});

// shadcn/ui-style owned primitive: native accessible button, variants and class merging.
export function Button({
  className,
  variant,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>) {
  return (
    <button className={cn(buttonVariants({ variant, className }))} {...props} />
  );
}
