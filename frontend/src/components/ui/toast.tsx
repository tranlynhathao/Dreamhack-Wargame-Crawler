import * as ToastPrimitive from "@radix-ui/react-toast";
import { cva, type VariantProps } from "class-variance-authority";
import { CheckCircle2, Info, TriangleAlert, XCircle } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { cn } from "@/lib/utils";

const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden rounded-md border p-4 pr-8 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:slide-in-from-top-2 data-[state=closed]:fade-out-80",
  {
    variants: {
      variant: {
        default: "bg-card text-card-foreground border-border",
        success: "bg-card text-card-foreground border-success/40",
        warning: "bg-card text-card-foreground border-warning/40",
        destructive: "bg-card text-card-foreground border-destructive/40",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

type ToastVariant = NonNullable<VariantProps<typeof toastVariants>["variant"]>;

interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastItem extends ToastOptions {
  id: string;
}

interface ToastContextValue {
  toast: (options: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const variantIcon: Record<ToastVariant, JSX.Element> = {
  default: <Info className="h-4 w-4 text-primary" />,
  success: <CheckCircle2 className="h-4 w-4 text-success" />,
  warning: <TriangleAlert className="h-4 w-4 text-warning" />,
  destructive: <XCircle className="h-4 w-4 text-destructive" />,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((options: ToastOptions) => {
    const id = crypto.randomUUID();
    setItems((prev) => [...prev, { id, variant: "default", ...options }]);
  }, []);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      <ToastPrimitive.Provider swipeDirection="right" duration={4500}>
        {children}
        {items.map((item) => (
          <ToastPrimitive.Root
            key={item.id}
            duration={item.duration}
            onOpenChange={(open) => {
              if (!open) dismiss(item.id);
            }}
            className={cn(toastVariants({ variant: item.variant ?? "default" }))}>
            <div className="mt-0.5">{variantIcon[item.variant ?? "default"]}</div>
            <div className="flex-1 space-y-1">
              <ToastPrimitive.Title className="text-sm font-medium leading-none">{item.title}</ToastPrimitive.Title>
              {item.description && (
                <ToastPrimitive.Description className="text-xs text-muted-foreground">
                  {item.description}
                </ToastPrimitive.Description>
              )}
            </div>
            <ToastPrimitive.Close
              aria-label="Dismiss"
              className="absolute right-2 top-2 rounded-sm p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
              <XCircle className="h-3.5 w-3.5" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed right-4 top-4 z-[100] flex max-h-screen w-full max-w-sm flex-col gap-2 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
