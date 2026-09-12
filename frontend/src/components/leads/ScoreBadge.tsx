import { clsx } from 'clsx';
import { Badge } from '../ui';

interface ScoreBadgeProps {
  score?: number;
  tier?: string;
  className?: string;
  showTierText?: boolean;
}

export function ScoreBadge({ score, tier, className, showTierText = false }: ScoreBadgeProps) {
  if (score === undefined || score === null) {
    return <Badge variant="outline" className={className}>Unscored</Badge>;
  }

  // Determine variant based on tier
  let variant: 'default' | 'success' | 'warning' | 'error' | 'info' | 'outline' = 'default';
  
  const normalizedTier = tier?.toUpperCase() || '';
  if (normalizedTier === 'HIGH') variant = 'success';
  else if (normalizedTier === 'MEDIUM') variant = 'warning';
  else if (normalizedTier === 'LOW') variant = 'error';
  else {
    // Fallback if no tier is provided, calculate based on score
    if (score >= 75) variant = 'success';
    else if (score >= 50) variant = 'warning';
    else variant = 'error';
  }

  const getTierText = () => {
    if (normalizedTier === 'HIGH') return 'High Value';
    if (normalizedTier === 'MEDIUM') return 'Medium';
    if (normalizedTier === 'LOW') return 'Low Quality';
    return '';
  };

  return (
    <div className={clsx("flex items-center gap-2", className)}>
      <Badge variant={variant} className="font-mono text-sm px-2 py-1">
        {Math.round(score)} / 100
      </Badge>
      {showTierText && tier && (
        <span className={clsx(
          "text-xs font-medium",
          variant === 'success' && "text-emerald-700",
          variant === 'warning' && "text-amber-700",
          variant === 'error' && "text-red-700"
        )}>
          {getTierText()}
        </span>
      )}
    </div>
  );
}
