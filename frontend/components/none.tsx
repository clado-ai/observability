import { cn } from "@/lib/utils";

export default function None({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: "normal";
}) {
  return (
    <p
      className={cn(
        "flex-1 text-center flex flex-col items-center justify-center",
        style !== "normal" && "text-muted-foreground text-xs",
      )}
    >
      {children}
    </p>
  );
}
