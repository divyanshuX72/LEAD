import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  indicatorClassName?: string;
}

export function Progress({ className, value = 0, max = 100, indicatorClassName, ...props }: ProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div
      className={cn("relative h-4 w-full overflow-hidden rounded-full bg-gray-100", className)}
      {...props}
    >
      <div
        className={cn("h-full w-full flex-1 bg-gray-900 transition-all duration-500 ease-in-out", indicatorClassName)}
        style={{ transform: `translateX(-${100 - percentage}%)` }}
      />
    </div>
  );
}
