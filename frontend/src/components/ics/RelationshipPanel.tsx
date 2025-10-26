/**
 * RelationshipPanel: Scrollable list of relationships with filtering
 */

import { useState, useMemo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { GitBranch } from 'lucide-react';
import { RelationshipCard } from './RelationshipCard';
import { useICSStore } from '@/lib/ics/store';
import type { RelationshipType } from '@/types/ics/semantic';

interface RelationshipPanelProps {
  className?: string;
}

export function RelationshipPanel({ className }: RelationshipPanelProps) {
  const { semanticAnalysis, selectedRelationship, selectRelationship } = useICSStore();
  const [filter, setFilter] = useState<RelationshipType | 'all'>('all');
  const [sortBy, setSortBy] = useState<'confidence' | 'type'>('confidence');

  const relationships = semanticAnalysis?.relationships || [];
  const entities = semanticAnalysis?.entities || [];

  // Filter and sort relationships
  const filteredRelationships = useMemo(() => {
    let filtered = relationships;

    // Apply type filter
    if (filter !== 'all') {
      filtered = filtered.filter((rel) => rel.type === filter);
    }

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      if (sortBy === 'confidence') {
        return b.confidence - a.confidence;
      }
      return a.type.localeCompare(b.type);
    });

    return sorted;
  }, [relationships, filter, sortBy]);

  // Count relationships by type
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {
      causal: 0,
      temporal: 0,
      conditional: 0,
      dependency: 0,
    };

    relationships.forEach((rel) => {
      counts[rel.type] = (counts[rel.type] || 0) + 1;
    });

    return counts;
  }, [relationships]);

  // Empty state
  if (relationships.length === 0) {
    return (
      <div className={className}>
        <div className="p-3 border-b border-border">
          <h2 className="text-sm font-semibold">Relationships</h2>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="text-center space-y-2">
            <GitBranch className="h-12 w-12 mx-auto text-muted-foreground opacity-50" />
            <p className="text-sm text-muted-foreground">No relationships detected</p>
            <p className="text-xs text-muted-foreground">
              Relationships will appear here after semantic analysis
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="p-3 border-b border-border space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">
            Relationships{' '}
            <Badge variant="secondary" className="ml-2">
              {filteredRelationships.length}
            </Badge>
          </h2>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          {/* Type filter */}
          <Select value={filter} onValueChange={(value) => setFilter(value as RelationshipType | 'all')}>
            <SelectTrigger className="h-8 text-xs flex-1">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types ({relationships.length})</SelectItem>
              <SelectItem value="causal">Causal ({typeCounts.causal})</SelectItem>
              <SelectItem value="temporal">Temporal ({typeCounts.temporal})</SelectItem>
              <SelectItem value="conditional">Conditional ({typeCounts.conditional})</SelectItem>
              <SelectItem value="dependency">Dependency ({typeCounts.dependency})</SelectItem>
            </SelectContent>
          </Select>

          {/* Sort */}
          <Select value={sortBy} onValueChange={(value) => setSortBy(value as 'confidence' | 'type')}>
            <SelectTrigger className="h-8 text-xs flex-1">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="confidence">Confidence</SelectItem>
              <SelectItem value="type">Type</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Relationship list */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-2" role="list" aria-label="Semantic relationships">
          {filteredRelationships.map((relationship) => (
            <div key={relationship.id} role="listitem">
              <RelationshipCard
                relationship={relationship}
                entities={entities}
                isSelected={selectedRelationship === relationship.id}
                onClick={() => selectRelationship(relationship.id)}
              />
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
