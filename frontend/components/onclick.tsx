"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function OnClick({
  children,
  onClick,
  props,
}: {
  children: React.ReactNode;
  onClick: () => void;
  props?: React.ComponentProps<typeof Button>;
}) {
  const [loading, setLoading] = useState(false);
  return (
    <Button
      onClick={() => {
        setLoading(true);
        onClick();
      }}
      disabled={loading}
      {...props}
    >
      {loading ? (
        <>
          {" "}
          <span className="animate-spin mr-2">↻</span>
          Loading...
        </>
      ) : (
        children
      )}
    </Button>
  );
}
