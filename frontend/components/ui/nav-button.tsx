"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NavButton({
  children,
  href,
  props,
  className,
}: {
  children: React.ReactNode;
  href: string;
  props?: React.ComponentProps<typeof Button>;
  className?: string;
}) {
  const pathname = usePathname();

  const isActive = pathname === href;
  return (
    <Link href={href} className="w-full">
      <Button
        variant="ghost"
        className={cn(
          "w-full justify-start",
          isActive && "bg-accent text-black cursor-default",
          className,
        )}
        {...props}
      >
        {children}
      </Button>
    </Link>
  );
}
