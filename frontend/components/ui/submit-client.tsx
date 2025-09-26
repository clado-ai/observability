"use client";

import type React from "react";
import { useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";

export default function SubmitButton({
  children,
  onClick,
  disabled,
  loading,
  className,
  variant,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  className?: string;
  variant?: "default" | "outline" | "ghost" | "secondary" | "link";
}) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const lastClickTime = useRef<number>(0);

  const handleClick = useCallback(() => {
    const now = Date.now();
    // Prevent rapid clicking (debounce for 1 second)
    if (now - lastClickTime.current < 1000) {
      return;
    }
    lastClickTime.current = now;
    onClick();
  }, [onClick]);

  return (
    <Button
      ref={buttonRef}
      onClick={handleClick}
      disabled={disabled || loading}
      className={className}
      variant={variant}
    >
      {loading ? (
        <>
          <span className="animate-spin mr-2">↻</span>
          Loading...
        </>
      ) : (
        children
      )}
    </Button>
  );
}
