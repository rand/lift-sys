/**
 * SolutionSpaceNarrowingView Component
 *
 * Displays before/after solution space comparison for a typed hole,
 * showing how constraints narrow the space of possible solutions.
 */

import React from 'react';
import { ArrowRight, Info, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import type { TypedHole, Constraint } from '@/types/ics/semantic';

interface SolutionSpaceNarrowingViewProps {
  hole: TypedHole;
  className?: string;
}

/**
 * Estimates solution space size based on constraints
 * Uses heuristic: each constraint reduces space by a percentage based on type
 */
function estimateSolutionSpace(constraints: Constraint[]): number {
  let baseSpace = 1000; // Initial solution space size

  constraints.forEach((constraint) => {
    switch (constraint.type) {
      case 'return_constraint':
        baseSpace *= 0.6; // 40% reduction
        break;
      case 'loop_constraint':
        baseSpace *= 0.7; // 30% reduction
        break;
      case 'position_constraint':
        baseSpace *= 0.8; // 20% reduction
        break;
      case 'temporal_constraint':
        baseSpace *= 0.7; // 30% reduction
        break;
      case 'conditional_constraint':
        baseSpace *= 0.5; // 50% reduction
        break;
      case 'logical_constraint':
        baseSpace *= 0.6; // 40% reduction
        break;
      default:
        baseSpace *= 0.75; // 25% reduction for unknown types
        break;
    }
  });

  return Math.max(1, Math.floor(baseSpace));
}

/**
 * Calculates reduction percentage between two solution spaces
 */
function calculateReduction(beforeSize: number, afterSize: number): number {
  if (beforeSize === 0) return 0;
  return Math.floor(((beforeSize - afterSize) / beforeSize) * 100);
}

/**
 * Determines constraint satisfaction status
 */
type ConstraintStatus = 'satisfied' | 'violated' | 'unknown';

function getConstraintStatus(constraint: Constraint, hole: TypedHole): ConstraintStatus {
  // Simple heuristic: if constraint is locked, it's satisfied
  if (constraint.locked) {
    return 'satisfied';
  }

  // If constraint has high severity, it might be violated
  if (constraint.severity === 'error') {
    return hole.resolved ? 'satisfied' : 'unknown';
  }

  return 'unknown';
}

/**
 * Returns icon and color for constraint status
 */
function getStatusIndicator(status: ConstraintStatus) {
  switch (status) {
    case 'satisfied':
      return { Icon: CheckCircle2, className: 'text-green-500' };
    case 'violated':
      return { Icon: XCircle, className: 'text-red-500' };
    case 'unknown':
      return { Icon: AlertCircle, className: 'text-yellow-500' };
  }
}

interface ConstraintListProps {
  constraints: Constraint[];
  hole: TypedHole;
  title: string;
}

function ConstraintList({ constraints, hole, title }: ConstraintListProps) {
  if (constraints.length === 0) {
    return (
      <div className="text-sm text-muted-foreground italic">
        No constraints
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">{title}</h4>
      <div className="space-y-1">
        {constraints.map((constraint) => {
          const status = getConstraintStatus(constraint, hole);
          const { Icon, className } = getStatusIndicator(status);

          return (
            <div
              key={constraint.id}
              className="flex items-start gap-2 p-2 rounded-md bg-muted/50 text-xs"
            >
              <Icon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', className)} />
              <div className="flex-1 space-y-1">
                <div className="font-medium">{constraint.description}</div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline" className="text-xs">
                    {constraint.type.replace('_', ' ')}
                  </Badge>
                  <Badge
                    variant={constraint.severity === 'error' ? 'destructive' : 'secondary'}
                    className="text-xs"
                  >
                    {constraint.severity}
                  </Badge>
                  <Badge variant="outline" className={cn('text-xs', className)}>
                    {status}
                  </Badge>
                </div>
                {constraint.impact && (
                  <div className="text-muted-foreground text-xs">
                    Impact: {constraint.impact}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function SolutionSpaceNarrowingView({ hole, className }: SolutionSpaceNarrowingViewProps) {
  // Get constraints from hole
  const constraints = hole.constraints || [];

  // For demonstration, we'll show "before" as empty and "after" as current constraints
  // In practice, this would track historical states
  const beforeConstraints: Constraint[] = [];
  const afterConstraints = constraints;

  const beforeSize = estimateSolutionSpace(beforeConstraints);
  const afterSize = estimateSolutionSpace(afterConstraints);
  const reductionPercentage = calculateReduction(beforeSize, afterSize);

  // Check if solution space is small enough to enumerate options
  const canEnumerateOptions = afterSize <= 10;

  // Calculate constraint satisfaction statistics
  const satisfiedCount = afterConstraints.filter(
    (c) => getConstraintStatus(c, hole) === 'satisfied'
  ).length;
  const violatedCount = afterConstraints.filter(
    (c) => getConstraintStatus(c, hole) === 'violated'
  ).length;
  const unknownCount = afterConstraints.filter(
    (c) => getConstraintStatus(c, hole) === 'unknown'
  ).length;

  return (
    <Card className={cn('solution-space-narrowing-card', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Info className="h-4 w-4 text-blue-500" />
          Solution Space Narrowing
        </CardTitle>
        <CardDescription className="text-xs">
          How constraints reduce possible solutions for {hole.identifier}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Before/After Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr,auto,1fr] gap-4 items-center">
          {/* Before */}
          <div className="space-y-2 p-3 rounded-md border">
            <h4 className="text-sm font-semibold text-muted-foreground">Before</h4>
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">
                {beforeConstraints.length === 0 ? 'No constraints' : `${beforeConstraints.length} constraints`}
              </div>
              <Badge variant="secondary" className="text-sm font-mono">
                ~{beforeSize.toLocaleString()} options
              </Badge>
            </div>
          </div>

          {/* Arrow */}
          <ArrowRight className="h-6 w-6 text-muted-foreground mx-auto animate-pulse" />

          {/* After */}
          <div className="space-y-2 p-3 rounded-md border border-primary/50 bg-primary/5">
            <h4 className="text-sm font-semibold">After</h4>
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">
                {afterConstraints.length} constraints applied
              </div>
              <Badge variant="default" className="text-sm font-mono">
                ~{afterSize.toLocaleString()} options
              </Badge>
            </div>
          </div>
        </div>

        {/* Reduction Alert */}
        {reductionPercentage > 0 && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-sm">
              Solution space reduced by <strong>{reductionPercentage}%</strong>
              {canEnumerateOptions && (
                <span className="ml-1">
                  (small enough to enumerate all options)
                </span>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Constraint Satisfaction Status */}
        {afterConstraints.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">Constraint Status</h4>
            <div className="grid grid-cols-3 gap-2">
              <div className="flex items-center gap-2 p-2 rounded-md bg-green-500/10">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <div className="text-xs">
                  <div className="font-medium">{satisfiedCount}</div>
                  <div className="text-muted-foreground">Satisfied</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-md bg-red-500/10">
                <XCircle className="h-4 w-4 text-red-500" />
                <div className="text-xs">
                  <div className="font-medium">{violatedCount}</div>
                  <div className="text-muted-foreground">Violated</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 rounded-md bg-yellow-500/10">
                <AlertCircle className="h-4 w-4 text-yellow-500" />
                <div className="text-xs">
                  <div className="font-medium">{unknownCount}</div>
                  <div className="text-muted-foreground">Unknown</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Detailed Constraint List */}
        {afterConstraints.length > 0 && (
          <div className="space-y-3">
            <ConstraintList
              constraints={afterConstraints}
              hole={hole}
              title="Active Constraints"
            />
          </div>
        )}

        {/* Option Enumeration (if small enough) */}
        {canEnumerateOptions && afterSize > 1 && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-xs">
              <strong>Suggestion:</strong> With only ~{afterSize} possible solutions,
              the system could enumerate all options for you to choose from.
            </AlertDescription>
          </Alert>
        )}

        {/* Fully Constrained */}
        {afterSize === 1 && (
          <Alert className="border-green-500 bg-green-500/10">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription className="text-sm">
              <strong>Fully constrained!</strong> Only one solution satisfies all constraints.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
