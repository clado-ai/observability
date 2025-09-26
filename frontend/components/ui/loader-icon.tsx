"use client";
import CliSpinners, { randomSpinner } from "cli-spinners";
import { useEffect, useMemo, useState } from "react";

const SPINNER_OPTIONS = [
  "dotsCircle",
  "sand",
  "line",
  "line2",
  "pipe",
  "star",
  "star2",
  "flip",
  "hamburger",
  "growVertical",
  "growHorizontal",
  "balloon",
  "balloon2",
  "noise",
  "boxBounce",
  "boxBounce2",
  "triangle",
  "arc",
  "smiley",
  "monkey",
  "hearts",
  "earth",
  "moon",
  "runner",
  "dqpb",
  "weather",
  "christmas",
  "layer",
  "fingerDance",
  "mindblown",
  "speaker",
  "orangePulse",
  "bluePulse",
  "orangeBluePulse",
  "timeTravel",
];

export default function LoaderIcon({
  allowBig = false,
  variant,
}: {
  allowBig?: boolean;
  variant?: "professional" | "cool";
}) {
  const [isClient, setIsClient] = useState(false);

  const spinner = useMemo(() => {
    if (variant === "professional") {
      return CliSpinners.dots2;
    }
    if (variant === "cool") {
      return CliSpinners.bouncingBall;
    }
    if (allowBig) return randomSpinner();
    const randomOption =
      SPINNER_OPTIONS[Math.floor(Math.random() * SPINNER_OPTIONS.length)];
    return CliSpinners[randomOption as keyof typeof CliSpinners];
  }, [allowBig, variant]);

  const [frame, setFrame] = useState(0);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient) return;

    const intervalId = setInterval(() => {
      setFrame((prev: number) => (prev + 1) % spinner.frames.length);
    }, spinner.interval);

    return () => clearInterval(intervalId);
  }, [spinner, isClient]);

  if (!isClient) {
    return <span className="min-w-8 inline-block text-center">🍉</span>;
  }

  return (
    <span className="min-w-8 inline-block text-center">
      {spinner.frames[frame]}
    </span>
  );
}
