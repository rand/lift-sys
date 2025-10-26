/**
 * ICSLayout: Main layout for the Integrated Context Studio
 *
 * 4-panel layout:
 * [MenuBar] [FileExplorer] [ActiveEditor] [SymbolsPanel + Inspector + AIChat]
 */

import { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { useICSStore } from '@/lib/ics/store';
import { MenuBar } from './MenuBar';
import { FileExplorer } from './FileExplorer';
import { ActiveEditor } from './ActiveEditor';
import { SymbolsPanel } from './SymbolsPanel';
import { HoleInspector } from './HoleInspector';
import { RelationshipPanel } from './RelationshipPanel';
import { AIChat } from './AIChat';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';

export function ICSLayout() {
  const { panelVisibility, layout, setLayout } = useICSStore();
  const [inspectorTab, setInspectorTab] = useState<'holes' | 'relationships'>('holes');

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-background">
      {/* Left menu bar */}
      <MenuBar />

      {/* Main content area */}
      <PanelGroup direction="horizontal" className="flex-1">
        {/* Left panel: File Explorer */}
        {panelVisibility.fileExplorer && (
          <>
            <Panel
              defaultSize={layout.leftPanelWidth}
              minSize={15}
              maxSize={40}
              onResize={(size) => setLayout({ leftPanelWidth: size })}
              className="border-r border-border"
            >
              <FileExplorer />
            </Panel>
            <PanelResizeHandle className="w-1 bg-border hover:bg-primary/20 transition-colors" />
          </>
        )}

        {/* Center panel: Active Editor */}
        <Panel defaultSize={100 - layout.leftPanelWidth - layout.rightPanelWidth} minSize={30}>
          <ActiveEditor />
        </Panel>

        {/* Right panel: Symbols + Inspector + Chat */}
        {(panelVisibility.symbolsPanel || panelVisibility.inspector || panelVisibility.chat) && (
          <>
            <PanelResizeHandle className="w-1 bg-border hover:bg-primary/20 transition-colors" />
            <Panel
              defaultSize={layout.rightPanelWidth}
              minSize={20}
              maxSize={50}
              onResize={(size) => setLayout({ rightPanelWidth: size })}
              className="border-l border-border"
            >
              <PanelGroup direction="vertical">
                {/* Top right: Symbols Panel + Inspector */}
                {(panelVisibility.symbolsPanel || panelVisibility.inspector) && (
                  <Panel defaultSize={60} minSize={30}>
                    <PanelGroup direction="vertical">
                      {/* Symbols Panel */}
                      {panelVisibility.symbolsPanel && (
                        <>
                          <Panel
                            defaultSize={50}
                            minSize={20}
                            onResize={(size) => setLayout({ inspectorHeight: 100 - size })}
                          >
                            <SymbolsPanel />
                          </Panel>
                          {panelVisibility.inspector && (
                            <PanelResizeHandle className="h-1 bg-border hover:bg-primary/20 transition-colors" />
                          )}
                        </>
                      )}

                      {/* Inspector: Holes + Relationships */}
                      {panelVisibility.inspector && (
                        <Panel defaultSize={layout.inspectorHeight} minSize={20}>
                          <Tabs value={inspectorTab} onValueChange={(v) => setInspectorTab(v as 'holes' | 'relationships')} className="h-full flex flex-col">
                            <div className="border-b border-border px-3 pt-2">
                              <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="holes">Holes</TabsTrigger>
                                <TabsTrigger value="relationships">Relationships</TabsTrigger>
                              </TabsList>
                            </div>
                            <TabsContent value="holes" className="flex-1 m-0">
                              <HoleInspector />
                            </TabsContent>
                            <TabsContent value="relationships" className="flex-1 m-0">
                              <RelationshipPanel className="h-full flex flex-col" />
                            </TabsContent>
                          </Tabs>
                        </Panel>
                      )}
                    </PanelGroup>
                  </Panel>
                )}

                {/* Bottom right: AI Chat */}
                {panelVisibility.chat &&
                  (panelVisibility.symbolsPanel || panelVisibility.inspector) && (
                    <PanelResizeHandle className="h-1 bg-border hover:bg-primary/20 transition-colors" />
                  )}
                {panelVisibility.chat && (
                  <Panel
                    defaultSize={layout.chatHeight}
                    minSize={20}
                    onResize={(size) => setLayout({ chatHeight: size })}
                  >
                    <AIChat />
                  </Panel>
                )}
              </PanelGroup>
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  );
}
