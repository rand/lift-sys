/**
 * ActiveEditor: Central content pane with tabbed views
 */

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useICSStore } from '@/lib/ics/store';
import { SemanticEditor } from './SemanticEditor';
import { FileText, Code, LayoutGrid, GitCompare } from 'lucide-react';

export function ActiveEditor() {
  const { activeTab, setActiveTab } = useICSStore();

  return (
    <div className="h-full flex flex-col">
      <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)} className="h-full flex flex-col">
        <div className="border-b border-border px-4">
          <TabsList className="h-10 bg-transparent">
            <TabsTrigger value="natural-language" className="gap-2">
              <FileText className="h-4 w-4" />
              Natural Language
            </TabsTrigger>
            <TabsTrigger value="ir" className="gap-2">
              <LayoutGrid className="h-4 w-4" />
              IR View
            </TabsTrigger>
            <TabsTrigger value="code" className="gap-2">
              <Code className="h-4 w-4" />
              Code
            </TabsTrigger>
            <TabsTrigger value="split" className="gap-2">
              <GitCompare className="h-4 w-4" />
              Split View
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 overflow-hidden">
          <TabsContent value="natural-language" className="h-full m-0 p-0">
            <SemanticEditor />
          </TabsContent>

          <TabsContent value="ir" className="h-full m-0 p-4">
            <div className="h-full border border-dashed border-border rounded-lg flex items-center justify-center">
              <div className="text-center space-y-2">
                <LayoutGrid className="h-12 w-12 mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">IR View</p>
                <p className="text-xs text-muted-foreground">Structured representation will appear here</p>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="code" className="h-full m-0 p-4">
            <div className="h-full border border-dashed border-border rounded-lg flex items-center justify-center">
              <div className="text-center space-y-2">
                <Code className="h-12 w-12 mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Code View</p>
                <p className="text-xs text-muted-foreground">Generated code will appear here</p>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="split" className="h-full m-0">
            <div className="h-full grid grid-cols-3 gap-0">
              <div className="border-r border-border">
                <SemanticEditor />
              </div>
              <div className="border-r border-border p-4">
                <div className="text-center space-y-2">
                  <LayoutGrid className="h-8 w-8 mx-auto text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">IR View</p>
                </div>
              </div>
              <div className="p-4">
                <div className="text-center space-y-2">
                  <Code className="h-8 w-8 mx-auto text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">Code View</p>
                </div>
              </div>
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
