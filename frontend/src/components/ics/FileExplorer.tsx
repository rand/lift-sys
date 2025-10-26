/**
 * FileExplorer: Tree view of files and assets
 */

import { useState } from 'react';
import { ChevronRight, ChevronDown, File, Folder, FolderOpen } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface FileNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
}

// Mock file tree
const mockFileTree: FileNode[] = [
  {
    name: 'docs',
    type: 'folder',
    path: '/docs',
    children: [
      { name: 'planning', type: 'folder', path: '/docs/planning', children: [
        { name: 'HOLE_INVENTORY.md', type: 'file', path: '/docs/planning/HOLE_INVENTORY.md' },
        { name: 'SESSION_STATE.md', type: 'file', path: '/docs/planning/SESSION_STATE.md' },
      ]},
      { name: 'supabase', type: 'folder', path: '/docs/supabase', children: [
        { name: 'SUPABASE_SCHEMA.md', type: 'file', path: '/docs/supabase/SUPABASE_SCHEMA.md' },
      ]},
    ],
  },
  {
    name: 'lift_sys',
    type: 'folder',
    path: '/lift_sys',
    children: [
      { name: 'ir', type: 'folder', path: '/lift_sys/ir', children: [
        { name: 'models.py', type: 'file', path: '/lift_sys/ir/models.py' },
        { name: 'constraints.py', type: 'file', path: '/lift_sys/ir/constraints.py' },
      ]},
      { name: 'dspy_signatures', type: 'folder', path: '/lift_sys/dspy_signatures', children: [
        { name: 'node_interface.py', type: 'file', path: '/lift_sys/dspy_signatures/node_interface.py' },
      ]},
    ],
  },
  {
    name: 'specifications',
    type: 'folder',
    path: '/specifications',
    children: [
      { name: 'example_spec.md', type: 'file', path: '/specifications/example_spec.md' },
    ],
  },
];

function FileTreeNode({ node, depth = 0 }: { node: FileNode; depth?: number }) {
  const [isExpanded, setIsExpanded] = useState(depth === 0);

  const handleClick = () => {
    if (node.type === 'folder') {
      setIsExpanded(!isExpanded);
    } else {
      console.log('Open file:', node.path);
    }
  };

  return (
    <div>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleClick}
        className="w-full justify-start gap-1 h-7 px-2 font-normal"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {node.type === 'folder' && (
          <>
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 shrink-0" />
            )}
            {isExpanded ? (
              <FolderOpen className="h-4 w-4 shrink-0 text-blue-500" />
            ) : (
              <Folder className="h-4 w-4 shrink-0 text-blue-500" />
            )}
          </>
        )}
        {node.type === 'file' && <File className="h-4 w-4 shrink-0 ml-5 text-muted-foreground" />}
        <span className="truncate text-sm">{node.name}</span>
      </Button>
      {node.type === 'folder' && isExpanded && node.children && (
        <div>
          {node.children.map((child, index) => (
            <FileTreeNode key={index} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileExplorer() {
  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b border-border">
        <h2 className="text-sm font-semibold">Files</h2>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-1">
          {mockFileTree.map((node, index) => (
            <FileTreeNode key={index} node={node} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
