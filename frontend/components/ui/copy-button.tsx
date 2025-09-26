"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function CopyButton({
  text,
  full,
}: {
  text: string;
  full?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };
  return (
    <Button
      variant="outline"
      size={full ? "default" : "icon"}
      onClick={handleCopy}
    >
      {copied ? (
        <>
          <i className="bx bx-check"></i>
          {full && "Copied"}
        </>
      ) : (
        <>
          <i className="bx bx-copy"></i>
          {full && "Copy"}
        </>
      )}
    </Button>
  );
}
