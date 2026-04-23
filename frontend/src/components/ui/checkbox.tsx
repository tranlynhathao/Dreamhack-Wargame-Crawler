import { Check, Minus } from "lucide-react";
import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  indeterminate?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked, indeterminate, ...props }, ref) => (
    <label
      className={cn(
        "relative inline-flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded-[4px] border border-input bg-background transition-colors hover:border-primary/60",
        (checked || indeterminate) && "border-primary bg-primary text-primary-foreground",
        className,
      )}>
      <input ref={ref} type="checkbox" checked={checked} className="peer sr-only" {...props} />
      {indeterminate ? (
        <Minus className="h-3 w-3" strokeWidth={3} />
      ) : checked ? (
        <Check className="h-3 w-3" strokeWidth={3} />
      ) : null}
    </label>
  ),
);
Checkbox.displayName = "Checkbox";
