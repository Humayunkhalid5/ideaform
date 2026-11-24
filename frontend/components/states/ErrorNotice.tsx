import { AlertTriangle, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ErrorNotice({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-card border border-if-danger/25 bg-if-danger/[0.06] p-4 text-[13px] text-if-danger sm:flex-row sm:items-center"
    >
      <AlertTriangle className="size-4 shrink-0" />
      <p className="flex-1 leading-snug">{message}</p>
      {onRetry && (
        <Button variant="ghost" size="sm" className="text-if-danger" onClick={onRetry}>
          <RotateCw className="size-3.5" /> Try again
        </Button>
      )}
    </div>
  );
}
