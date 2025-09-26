import { cn } from "@/lib/utils";

export default function Subtitle({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-xs font-semibold text-gray-400 uppercase tracking-wide",
        className,
      )}
    >
      {text}
    </p>
  );
}
