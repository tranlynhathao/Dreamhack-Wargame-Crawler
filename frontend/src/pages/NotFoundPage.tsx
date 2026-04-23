import { FileQuestion } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <EmptyState
      icon={FileQuestion}
      title="Page not found"
      description="The route you tried to open doesn't exist in this console."
      action={
        <Button asChild size="sm" variant="outline">
          <Link to="/dashboard">Back to dashboard</Link>
        </Button>
      }
    />
  );
}
