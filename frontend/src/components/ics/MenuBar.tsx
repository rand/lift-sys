/**
 * MenuBar: Left-side icon navigation bar
 */

import {
  FileText,
  Search,
  GitBranch,
  Settings,
  Terminal,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useICSStore } from '@/lib/ics/store';
import { cn } from '@/lib/utils';

export function MenuBar() {
  const { panelVisibility, setPanelVisibility } = useICSStore();

  const toggleFileExplorer = () => {
    setPanelVisibility('fileExplorer', !panelVisibility.fileExplorer);
  };

  const menuItems = [
    { icon: FileText, label: 'Files', action: toggleFileExplorer, active: panelVisibility.fileExplorer },
    { icon: Search, label: 'Search', action: () => console.log('Search'), active: false },
    { icon: GitBranch, label: 'Source Control', action: () => console.log('Git'), active: false },
    { icon: Terminal, label: 'Terminal', action: () => setPanelVisibility('terminal', !panelVisibility.terminal), active: panelVisibility.terminal },
    { icon: Settings, label: 'Settings', action: () => console.log('Settings'), active: false },
  ];

  return (
    <div className="w-12 bg-muted/30 border-r border-border flex flex-col items-center py-2 gap-1">
      <TooltipProvider delayDuration={300}>
        {menuItems.map((item, index) => (
          <Tooltip key={index}>
            <TooltipTrigger asChild>
              <Button
                variant={item.active ? 'secondary' : 'ghost'}
                size="icon"
                onClick={item.action}
                className={cn(
                  'w-10 h-10',
                  item.active && 'bg-secondary text-secondary-foreground'
                )}
              >
                <item.icon className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p>{item.label}</p>
            </TooltipContent>
          </Tooltip>
        ))}
      </TooltipProvider>
    </div>
  );
}
