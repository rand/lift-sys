/**
 * HoleInspector: Detailed view of selected hole
 */

import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useICSStore } from '@/lib/ics/store';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  XCircle,
  AlertCircle,
  Lightbulb,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ConstraintPropagationView } from './ConstraintPropagationView';

export function HoleInspector() {
  const { selectedHole, holes, constraintPropagationHistory } = useICSStore();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    dependencies: true,
    constraints: true,
    solutionSpace: false,
    criteria: false,
    refinements: false,
    propagation: true,
  });

  const hole = selectedHole ? holes.get(selectedHole) : null;

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  if (!hole) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-3 border-b border-border">
          <h2 className="text-sm font-semibold">Hole Inspector</h2>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="text-center space-y-2">
            <Circle className="h-12 w-12 mx-auto text-muted-foreground opacity-50" />
            <p className="text-sm text-muted-foreground">Select a hole to inspect</p>
          </div>
        </div>
      </div>
    );
  }

  const statusIcon = {
    unresolved: <Circle className="h-4 w-4 text-orange-500" />,
    in_progress: <AlertCircle className="h-4 w-4 text-blue-500" />,
    resolved: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  }[hole.status];

  const kindColors = {
    intent: 'bg-blue-500',
    signature: 'bg-green-500',
    effect: 'bg-yellow-500',
    assertion: 'bg-purple-500',
    implementation: 'bg-gray-500',
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-border">
        <h2 className="text-sm font-semibold">Hole Inspector</h2>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {/* Header */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              {statusIcon}
              <h3 className="text-lg font-bold">{hole.identifier}</h3>
            </div>
            <div className="flex flex-wrap gap-1">
              <Badge className={cn('text-white', kindColors[hole.kind])}>{hole.kind}</Badge>
              <Badge variant="outline">{hole.status}</Badge>
              <Badge variant="secondary">{hole.priority}</Badge>
              <Badge variant="outline">Phase {hole.phase}</Badge>
            </div>
          </div>

          {/* Type & Description */}
          <div className="space-y-1">
            <p className="text-sm"><span className="font-semibold">Type:</span> {hole.typeHint}</p>
            {hole.description && (
              <p className="text-sm text-muted-foreground">{hole.description}</p>
            )}
          </div>

          <Separator />

          {/* Dependencies */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('dependencies')}
              className="flex items-center gap-1 text-sm font-semibold hover:text-primary transition-colors"
            >
              {expandedSections.dependencies ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Dependencies ({hole.blocks.length + hole.blockedBy.length})
            </button>
            {expandedSections.dependencies && (
              <div className="pl-5 space-y-2">
                {hole.blocks.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Blocks ({hole.blocks.length})</p>
                    {hole.blocks.map((dep) => (
                      <div key={dep.id} className="text-xs p-1.5 rounded bg-muted">
                        <p className="font-medium">{dep.name}</p>
                        <p className="text-muted-foreground">{dep.reason}</p>
                      </div>
                    ))}
                  </div>
                )}
                {hole.blockedBy.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Blocked by ({hole.blockedBy.length})</p>
                    {hole.blockedBy.map((dep) => (
                      <div key={dep.id} className="text-xs p-1.5 rounded bg-muted">
                        <p className="font-medium">{dep.name}</p>
                        <p className="text-muted-foreground">{dep.reason}</p>
                      </div>
                    ))}
                  </div>
                )}
                {hole.blocks.length === 0 && hole.blockedBy.length === 0 && (
                  <p className="text-xs text-muted-foreground">No dependencies</p>
                )}
              </div>
            )}
          </div>

          <Separator />

          {/* Constraints */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('constraints')}
              className="flex items-center gap-1 text-sm font-semibold hover:text-primary transition-colors"
            >
              {expandedSections.constraints ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Constraints ({hole.constraints?.length || 0})
            </button>
            {expandedSections.constraints && (
              <div className="pl-5 space-y-2">
                {hole.constraints && hole.constraints.length > 0 ? (
                  hole.constraints.map((constraintId, index) => (
                    <div key={index} className="text-xs p-2 rounded border border-border">
                      <p className="font-medium">Constraint {index + 1}</p>
                      <p className="text-muted-foreground">{constraintId}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground">No constraints applied</p>
                )}
              </div>
            )}
          </div>

          <Separator />

          {/* Solution Space */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('solutionSpace')}
              className="flex items-center gap-1 text-sm font-semibold hover:text-primary transition-colors"
            >
              {expandedSections.solutionSpace ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Solution Space
            </button>
            {expandedSections.solutionSpace && (
              <div className="pl-5 space-y-2 text-xs">
                <div>
                  <p className="text-muted-foreground">Before:</p>
                  <p className="font-medium">{hole.solutionSpace.before}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">After:</p>
                  <p className="font-medium">{hole.solutionSpace.after}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Reduction:</p>
                  <Badge variant="secondary">{hole.solutionSpace.reduction}%</Badge>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Acceptance Criteria */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('criteria')}
              className="flex items-center gap-1 text-sm font-semibold hover:text-primary transition-colors"
            >
              {expandedSections.criteria ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Acceptance Criteria ({hole.acceptanceCriteria.length})
            </button>
            {expandedSections.criteria && (
              <div className="pl-5 space-y-1">
                {hole.acceptanceCriteria.length > 0 ? (
                  hole.acceptanceCriteria.map((criterion, index) => (
                    <div key={index} className="flex items-start gap-2 text-xs">
                      {criterion.status === 'passing' ? (
                        <CheckCircle2 className="h-3 w-3 text-green-500 shrink-0 mt-0.5" />
                      ) : criterion.status === 'failing' ? (
                        <XCircle className="h-3 w-3 text-red-500 shrink-0 mt-0.5" />
                      ) : (
                        <Circle className="h-3 w-3 text-gray-400 shrink-0 mt-0.5" />
                      )}
                      <p>{criterion.description}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground">No criteria defined</p>
                )}
              </div>
            )}
          </div>

          <Separator />

          {/* AI Refinements */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('refinements')}
              className="flex items-center gap-1 text-sm font-semibold hover:text-primary transition-colors"
            >
              {expandedSections.refinements ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              AI Suggestions ({hole.refinements.length})
            </button>
            {expandedSections.refinements && (
              <div className="pl-5 space-y-2">
                {hole.refinements.length > 0 ? (
                  hole.refinements.map((refinement, index) => (
                    <div key={index} className="p-2 rounded bg-blue-500/10 border border-blue-500/20 space-y-1">
                      <div className="flex items-start gap-2">
                        <Lightbulb className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
                        <p className="text-xs font-medium flex-1">{refinement.suggestion}</p>
                      </div>
                      <p className="text-xs text-muted-foreground pl-6">{refinement.rationale}</p>
                      <div className="flex items-center gap-2 pl-6">
                        <Badge variant="secondary" className="text-xs">
                          {(refinement.confidence * 100).toFixed(0)}% confident
                        </Badge>
                        <span className="text-xs text-muted-foreground">{refinement.impact}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground">No suggestions available</p>
                )}
              </div>
            )}
          </div>

          {/* Constraint Propagation History */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('propagation')}
              className="flex items-center gap-1 text-sm font-semibold hover:text-primary transition-colors"
            >
              {expandedSections.propagation ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              Propagation History (
              {constraintPropagationHistory.filter(
                (e) => e.sourceHole === selectedHole || e.targetHole === selectedHole
              ).length}
              )
            </button>
            {expandedSections.propagation && (
              <div className="pl-5 space-y-2">
                {constraintPropagationHistory.filter(
                  (e) => e.sourceHole === selectedHole || e.targetHole === selectedHole
                ).length > 0 ? (
                  constraintPropagationHistory
                    .filter((e) => e.sourceHole === selectedHole || e.targetHole === selectedHole)
                    .slice(-3)
                    .reverse()
                    .map((event) => (
                      <ConstraintPropagationView key={event.id} event={event} />
                    ))
                ) : (
                  <p className="text-xs text-muted-foreground">
                    No propagation events for this hole yet
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="pt-2 flex gap-2">
            <Button size="sm" className="flex-1">Refine</Button>
            <Button size="sm" variant="outline" className="flex-1">View Tests</Button>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
