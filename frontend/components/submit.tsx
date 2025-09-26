"use client";

import type React from "react";
import { useRef } from "react";
import { useFormStatus } from "react-dom";
import { Button } from "./ui/button";

export default function SubmitButton({
  children,
  className,
  variant,
}: {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "outline" | "ghost" | "secondary" | "link";
}) {
  const { pending } = useFormStatus();
  const buttonRef = useRef<HTMLButtonElement>(null);

  return (
    <Button
      ref={buttonRef}
      type="submit"
      disabled={pending}
      className={className}
      variant={variant}
    >
      {pending ? (
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
