/**
 * ConstraintPropagationView component
 * Visualizes constraint propagation from resolved holes to dependent holes
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowRight, CheckCircle2, AlertTriangle, TrendingDown } from 'lucide-react';
import type { ConstraintPropagationEvent } from '@/types/ics/semantic';
import { cn } from '@/lib/utils';

interface ConstraintPropagationViewProps {
  event: ConstraintPropagationEvent;
  className?: string;
}

export function ConstraintPropagationView({ event, className }: ConstraintPropagationViewProps) {
  const { sourceHole, targetHole, addedConstraints, solutionSpaceReduction, status } = event;

  return (
    <Card className={cn('constraint-propagation-card', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          Constraint Propagation
        </CardTitle>
        <CardDescription className="text-xs">
          {new Date(event.timestamp).toLocaleTimeString()}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Source and target holes */}
        <div className="flex items-center gap-2">
          <div className="flex-1">
            <div className="text-xs text-muted-foreground mb-1">From</div>
            <Badge variant="secondary" className="font-mono text-xs">
              {sourceHole}
            </Badge>
          </div>

          <ArrowRight className="h-5 w-5 text-muted-foreground animate-pulse" />

          <div className="flex-1">
            <div className="text-xs text-muted-foreground mb-1">To</div>
            <Badge variant="outline" className="font-mono text-xs">
              {targetHole}
            </Badge>
          </div>
        </div>

        {/* Added constraints */}
        <div className="space-y-2">
          <div className="text-xs font-medium">
            Added Constraints ({addedConstraints.length})
          </div>
          {addedConstraints.map((constraint) => (
            <Alert key={constraint.id} className="py-2">
              <AlertTriangle className="h-3 w-3" />
              <AlertDescription className="text-xs">
                <div className="font-medium">{constraint.type}</div>
                <div className="text-muted-foreground">{constraint.description}</div>
              </AlertDescription>
            </Alert>
          ))}
        </div>

        {/* Solution space reduction */}
        <div className="space-y-2">
          <div className="text-xs font-medium flex items-center gap-2">
            <TrendingDown className="h-3 w-3 text-blue-500" />
            Solution Space Narrowing
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Before</div>
              <div className="text-sm font-mono">
                {solutionSpaceReduction.before.toLocaleString()}
              </div>
            </div>
            <div className="space-y-1">
              <ArrowRight className="h-4 w-4 mx-auto text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">After</div>
              <div className="text-sm font-mono">
                {solutionSpaceReduction.after.toLocaleString()}
              </div>
            </div>
          </div>
          <Alert className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
            <TrendingDown className="h-3 w-3 text-blue-500" />
            <AlertDescription className="text-xs text-blue-900 dark:text-blue-100">
              Solution space reduced by{' '}
              <span className="font-bold">{solutionSpaceReduction.percentage}%</span>
            </AlertDescription>
          </Alert>
        </div>

        {/* Status */}
        {status === 'failed' && (
          <Alert variant="destructive">
            <AlertDescription className="text-xs">
              Propagation failed
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * ConstraintPropagationHistory component
 * Shows a timeline of all constraint propagations
 */

interface ConstraintPropagationHistoryProps {
  events: ConstraintPropagationEvent[];
  maxEvents?: number;
  className?: string;
}

export function ConstraintPropagationHistory({
  events,
  maxEvents = 10,
  className,
}: ConstraintPropagationHistoryProps) {
  const displayEvents = events.slice(-maxEvents).reverse();

  if (events.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-sm">Constraint Propagation History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-xs text-muted-foreground text-center py-4">
            No constraint propagations yet. Resolve a hole to see propagation in action.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium">
          Constraint Propagation History
        </h3>
        <Badge variant="secondary" className="text-xs">
          {events.length} {events.length === 1 ? 'event' : 'events'}
        </Badge>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {displayEvents.map((event) => (
          <ConstraintPropagationView key={event.id} event={event} />
        ))}
      </div>

      {events.length > maxEvents && (
        <div className="text-xs text-muted-foreground text-center pt-2">
          Showing last {maxEvents} of {events.length} events
        </div>
      )}
    </div>
  );
}
