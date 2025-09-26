"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };
  return (
    <Button variant="outline" size={"icon"} onClick={handleCopy}>
      {copied ? (
        <i className="bx bx-check"></i>
      ) : (
        <i className="bx bx-copy"></i>
      )}
    </Button>
  );
}
