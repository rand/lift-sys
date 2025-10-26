/**
 * SymbolsPanel: Visualization of entities, holes, and constraints
 */

import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useICSStore } from '@/lib/ics/store';
import { Circle, Square, Hexagon, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SymbolsPanel() {
  const { semanticAnalysis, holes, constraints, selectedHole, selectHole } = useICSStore();

  const holesArray = Array.from(holes.values());
  const unresolvedHoles = holesArray.filter((h) => h.status === 'unresolved');
  const inProgressHoles = holesArray.filter((h) => h.status === 'in_progress');
  const resolvedHoles = holesArray.filter((h) => h.status === 'resolved');

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-border">
        <h2 className="text-sm font-semibold">Symbols & Holes</h2>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {/* Entities Section */}
          {semanticAnalysis && semanticAnalysis.entities.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Entities ({semanticAnalysis.entities.length})
              </h3>
              <div className="flex flex-wrap gap-1">
                {semanticAnalysis.entities.slice(0, 20).map((entity) => (
                  <Badge
                    key={entity.id}
                    variant="secondary"
                    className="text-xs gap-1"
                  >
                    <Circle className="h-2 w-2 fill-current" />
                    {entity.text}
                  </Badge>
                ))}
                {semanticAnalysis.entities.length > 20 && (
                  <Badge variant="outline" className="text-xs">
                    +{semanticAnalysis.entities.length - 20} more
                  </Badge>
                )}
              </div>
            </div>
          )}

          {/* Typed Holes Section */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Typed Holes ({holesArray.length})
            </h3>

            {/* Unresolved Holes */}
            {unresolvedHoles.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Unresolved ({unresolvedHoles.length})</p>
                {unresolvedHoles.map((hole) => (
                  <button
                    key={hole.identifier}
                    onClick={() => selectHole(hole.identifier)}
                    className={cn(
                      'w-full text-left p-2 rounded-md border transition-colors',
                      'hover:bg-accent hover:border-accent-foreground',
                      selectedHole === hole.identifier
                        ? 'bg-accent border-accent-foreground'
                        : 'border-border'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Square className="h-4 w-4 text-orange-500" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{hole.identifier}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {hole.kind} · {hole.typeHint}
                        </p>
                      </div>
                      <Badge variant="outline" className="text-xs shrink-0">
                        {hole.priority}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* In Progress Holes */}
            {inProgressHoles.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">In Progress ({inProgressHoles.length})</p>
                {inProgressHoles.map((hole) => (
                  <button
                    key={hole.identifier}
                    onClick={() => selectHole(hole.identifier)}
                    className={cn(
                      'w-full text-left p-2 rounded-md border transition-colors',
                      'hover:bg-accent hover:border-accent-foreground',
                      selectedHole === hole.identifier
                        ? 'bg-accent border-accent-foreground'
                        : 'border-border'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Square className="h-4 w-4 text-blue-500" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{hole.identifier}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {hole.kind} · {hole.typeHint}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Resolved Holes */}
            {resolvedHoles.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Resolved ({resolvedHoles.length})</p>
                {resolvedHoles.slice(0, 5).map((hole) => (
                  <button
                    key={hole.identifier}
                    onClick={() => selectHole(hole.identifier)}
                    className={cn(
                      'w-full text-left p-2 rounded-md border opacity-60 transition-opacity',
                      'hover:opacity-100',
                      selectedHole === hole.identifier ? 'opacity-100' : ''
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Square className="h-4 w-4 text-green-500" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{hole.identifier}</p>
                        <p className="text-xs text-muted-foreground truncate">{hole.kind}</p>
                      </div>
                    </div>
                  </button>
                ))}
                {resolvedHoles.length > 5 && (
                  <p className="text-xs text-muted-foreground pl-2">
                    +{resolvedHoles.length - 5} more resolved
                  </p>
                )}
              </div>
            )}

            {holesArray.length === 0 && (
              <div className="text-center py-8 text-sm text-muted-foreground">
                No typed holes detected
              </div>
            )}
          </div>

          {/* Constraints Section */}
          {semanticAnalysis && semanticAnalysis.constraints.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Constraints ({semanticAnalysis.constraints.length})
              </h3>
              <div className="space-y-1">
                {semanticAnalysis.constraints.slice(0, 10).map((constraint) => (
                  <div
                    key={constraint.id}
                    className="flex items-start gap-2 p-2 rounded-md border border-border"
                  >
                    <Hexagon className="h-4 w-4 text-orange-500 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs truncate">{constraint.description}</p>
                      <div className="flex items-center gap-1 mt-1">
                        <Badge variant={constraint.severity === 'error' ? 'destructive' : 'secondary'} className="text-xs">
                          {constraint.severity}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{constraint.type}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ambiguities Section */}
          {semanticAnalysis && semanticAnalysis.ambiguities.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Ambiguities ({semanticAnalysis.ambiguities.length})
              </h3>
              <div className="space-y-1">
                {semanticAnalysis.ambiguities.map((ambiguity) => (
                  <div
                    key={ambiguity.id}
                    className="flex items-start gap-2 p-2 rounded-md bg-yellow-500/10 border border-yellow-500/20"
                  >
                    <AlertCircle className="h-4 w-4 text-yellow-600 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">"{ambiguity.text}"</p>
                      <p className="text-xs text-muted-foreground">{ambiguity.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
