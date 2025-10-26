/**
 * RelationshipCard: Display a single relationship with color-coded badge and confidence
 */

import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Card } from '@/components/ui/card';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Relationship, Entity } from '@/types/ics/semantic';

interface RelationshipCardProps {
  relationship: Relationship;
  entities: Entity[];
  isSelected?: boolean;
  onClick?: () => void;
}

// Color mapping for relationship types
const relationshipColors = {
  causal: 'bg-purple-500 hover:bg-purple-600',
  temporal: 'bg-cyan-500 hover:bg-cyan-600',
  conditional: 'bg-amber-500 hover:bg-amber-600',
  dependency: 'bg-teal-500 hover:bg-teal-600',
} as const;

// Confidence color thresholds
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.9) return 'bg-green-500';
  if (confidence >= 0.7) return 'bg-yellow-500';
  return 'bg-gray-500';
};

// Confidence text color
const getConfidenceTextColor = (confidence: number): string => {
  if (confidence >= 0.9) return 'text-green-600';
  if (confidence >= 0.7) return 'text-yellow-600';
  return 'text-gray-600';
};

export function RelationshipCard({
  relationship,
  entities,
  isSelected = false,
  onClick,
}: RelationshipCardProps) {
  const sourceEntity = entities.find((e) => e.id === relationship.source);
  const targetEntity = entities.find((e) => e.id === relationship.target);

  const confidencePercent = Math.round(relationship.confidence * 100);

  return (
    <Card
      className={cn(
        'p-3 cursor-pointer transition-all hover:shadow-md',
        isSelected && 'ring-2 ring-primary shadow-lg',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2'
      )}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      tabIndex={0}
      role="button"
      aria-label={`Relationship: ${relationship.type} from ${sourceEntity?.text || 'unknown'} to ${targetEntity?.text || 'unknown'}, confidence ${confidencePercent}%`}
    >
      <div className="space-y-2">
        {/* Relationship flow: Source -> Type -> Target */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Source entity */}
          <Badge variant="outline" className="font-medium">
            {sourceEntity?.text || relationship.source}
          </Badge>

          {/* Arrow */}
          <ArrowRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />

          {/* Relationship type badge */}
          <Badge className={cn('text-white font-semibold', relationshipColors[relationship.type])}>
            {relationship.type.toUpperCase()}
          </Badge>

          {/* Arrow */}
          <ArrowRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />

          {/* Target entity */}
          <Badge variant="outline" className="font-medium">
            {targetEntity?.text || relationship.target}
          </Badge>
        </div>

        {/* Confidence indicator */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Confidence</span>
            <span className={cn('text-xs font-semibold', getConfidenceTextColor(relationship.confidence))}>
              {confidencePercent}%
            </span>
          </div>
          <Progress
            value={confidencePercent}
            className="h-1.5"
            aria-label={`Confidence: ${confidencePercent}%`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={confidencePercent}
            style={
              {
                '--progress-background': getConfidenceColor(relationship.confidence),
              } as React.CSSProperties
            }
          />
        </div>

        {/* Description */}
        {relationship.text && (
          <p className="text-xs text-muted-foreground italic line-clamp-2">{relationship.text}</p>
        )}
      </div>
    </Card>
  );
}
