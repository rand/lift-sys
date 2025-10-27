---
track: ics
document_type: improvement_plan
status: planning
priority: P2
completion: 0%
last_updated: 2025-10-11
session_protocol: |
  For new Claude Code session:
  1. Design system improvement plan is PLANNED (not started)
  2. 23 tasks prioritized by impact/effort: 8 high, 10 medium, 5 low priority
  3. Timeline: 2-4 weeks (3 sprints)
  4. Based on: Design System Test Report findings
  5. Use this when beginning design system optimization work
related_docs:
  - docs/tracks/ics/ICS_RESUME_GUIDE.md
  - docs/tracks/ics/ICS_STATUS.md
  - docs/MASTER_ROADMAP.md
---

# Design System Improvement Plan
**Version**: 1.0
**Date**: October 11, 2025
**Based On**: Design System Test Report
**Timeline**: 2-4 weeks (3 sprints)

---

## Executive Summary

This plan outlines improvements and optimizations for the lift-sys design system, prioritized by **impact** and **effort**. All items are categorized into three sprints with clear success criteria.

**Total Tasks**: 23
**High Priority**: 8
**Medium Priority**: 10
**Low Priority**: 5

---

## Priority Matrix

```
High Impact, Low Effort:    ⭐⭐⭐ DO FIRST
High Impact, High Effort:   ⭐⭐ DO NEXT
Low Impact, Low Effort:     ⭐ QUICK WINS
Low Impact, High Effort:    💤 DEFER
```

---

## Sprint 1: Critical Path (Week 1)
**Goal**: Migrate views and fix critical issues
**Duration**: 5 days
**Priority**: HIGH

### 1.1 Migrate ConfigurationView ⭐⭐⭐
**Priority**: High
**Impact**: High (template for other views)
**Effort**: Low (2 hours)
**Assignee**: Frontend Developer

**Current State**:
- 15 inline styles
- Hardcoded colors (#94a3b8, #334155, etc.)
- Manual CSS objects

**Target State**:
```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function ConfigurationView() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="endpoint">Endpoint</Label>
          <Input id="endpoint" value={endpoint} onChange={...} />
        </div>
        {/* ... */}
      </CardContent>
    </Card>
  );
}
```

**Success Criteria**:
- ✅ Zero inline styles
- ✅ All inputs use Label + Input components
- ✅ Card uses composable structure
- ✅ Tailwind classes for all spacing

**Files to Change**:
- `frontend/src/views/ConfigurationView.tsx`

---

### 1.2 Migrate SignInView ⭐⭐⭐
**Priority**: High
**Impact**: High (first user touchpoint)
**Effort**: Low (1 hour)

**Current State**:
- 5 inline styles
- Inline flexbox styling
- Hardcoded colors for error messages

**Target State**:
```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

export function SignInView() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Welcome to lift-sys</CardTitle>
          <CardDescription>
            Sign in to connect your AI providers...
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* OAuth buttons */}
        </CardContent>
      </Card>
      {errorMessage && (
        <Alert variant="destructive">
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
```

**Success Criteria**:
- ✅ Card-based layout
- ✅ Error messages use Alert component
- ✅ Responsive (works on mobile)

---

### 1.3 Add Skip Links for Accessibility ⭐⭐⭐
**Priority**: High
**Impact**: High (accessibility requirement)
**Effort**: Low (1 hour)

**Implementation**:

Create `frontend/src/components/skip-link.tsx`:
```tsx
export function SkipLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-brand focus:text-brand-foreground focus:rounded-lg"
    >
      {children}
    </a>
  );
}
```

Add to `App.tsx`:
```tsx
<>
  <SkipLink href="#main-content">Skip to main content</SkipLink>
  <div className="main-shell">
    {/* ... */}
    <main id="main-content" className="p-8 bg-background overflow-auto">
      {/* ... */}
    </main>
  </div>
</>
```

**Success Criteria**:
- ✅ Skip link visible on keyboard focus
- ✅ Links to #main-content
- ✅ Keyboard accessible (Tab to focus)

---

### 1.4 Implement Bundle Code Splitting ⭐⭐
**Priority**: High
**Impact**: High (performance)
**Effort**: Medium (4 hours)

**Problem**: Main chunk is 552 kB (>500 kB threshold)

**Solution**: Dynamic imports for heavy components

**Implementation**:

Update `vite.config.ts`:
```typescript
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks
          'react-vendor': ['react', 'react-dom'],
          'query-vendor': ['@tanstack/react-query'],

          // UI chunks
          'ui-core': [
            './src/components/ui/button.tsx',
            './src/components/ui/input.tsx',
            './src/components/ui/card.tsx',
          ],
          'ui-forms': [
            './src/components/ui/select.tsx',
            './src/components/ui/checkbox.tsx',
            './src/components/ui/radio-group.tsx',
          ],
          'ui-overlays': [
            './src/components/ui/dialog.tsx',
            './src/components/ui/popover.tsx',
            './src/components/ui/dropdown-menu.tsx',
          ],
        },
      },
    },
  },
});
```

Use React.lazy for views:
```tsx
const ConfigurationView = lazy(() => import('./views/ConfigurationView'));
const RepositoryView = lazy(() => import('./views/RepositoryView'));
// ...

<Suspense fallback={<LoadingSpinner />}>
  {section === "configuration" && <ConfigurationView />}
</Suspense>
```

**Success Criteria**:
- ✅ Main chunk < 300 kB
- ✅ Vendor chunk separated
- ✅ UI components chunked logically
- ✅ Initial load time < 500ms (simulated)

**Expected Outcome**:
- Main: ~200 kB
- React Vendor: ~150 kB
- UI Core: ~80 kB
- UI Forms: ~70 kB
- UI Overlays: ~50 kB

---

## Sprint 2: View Migration (Week 2)
**Goal**: Migrate remaining views to design system
**Duration**: 5 days
**Priority**: MEDIUM-HIGH

### 2.1 Migrate PromptWorkbenchView ⭐⭐
**Priority**: High
**Impact**: High (core feature)
**Effort**: Medium (4 hours)
**Inline Styles**: 30

**Migration Tasks**:
- Replace `<textarea>` with `<Textarea>`
- Use `<Card>` for session list
- Add `<Badge>` for status indicators
- Use `<Alert>` for error messages
- Use `<Button>` variants consistently

**Success Criteria**:
- ✅ Zero inline styles
- ✅ Consistent spacing (space-y-4, gap-3)
- ✅ All form elements use design system

---

### 2.2 Migrate RepositoryView ⭐⭐
**Priority**: High
**Impact**: High (core feature)
**Effort**: Medium (4 hours)
**Inline Styles**: 25

**Migration Tasks**:
- Timeline to use `<Card>` components
- Status badges to use `<Badge variant="...">`
- Progress indicators to use `<Progress>`
- Input fields to use `<Input>` + `<Label>`
- Actions to use `<Button>` variants

**Success Criteria**:
- ✅ Timeline visually consistent
- ✅ Status badges use semantic variants
- ✅ Zero inline styles

---

### 2.3 Migrate EnhancedIrView ⭐⭐
**Priority**: Medium
**Impact**: Medium
**Effort**: Medium (3 hours)
**Inline Styles**: 20

**Migration Tasks**:
- IR display to use `<Card>` components
- Syntax highlighting containers to use design system
- Add `<Separator>` between sections
- Use `<Tabs>` if multiple views exist

---

### 2.4 Migrate IdeView ⭐⭐
**Priority**: Medium
**Impact**: Medium
**Effort**: Medium (3 hours)
**Inline Styles**: 18

**Migration Tasks**:
- Code editor container to use `<Card>`
- Console output to use `<Card>`
- Use `<Tabs>` for editor tabs
- Status bar to use design system

---

### 2.5 Migrate PlannerView ⭐
**Priority**: Medium
**Impact**: Medium
**Effort**: Low (2 hours)
**Inline Styles**: 15

---

### 2.6 Migrate IrView ⭐
**Priority**: Medium
**Impact**: Medium
**Effort**: Low (2 hours)
**Inline Styles**: 12

---

## Sprint 3: Enhancements (Week 3)
**Goal**: Polish, optimize, and enhance
**Duration**: 5 days
**Priority**: MEDIUM

### 3.1 Add Toast Notification System ⭐⭐⭐
**Priority**: High
**Impact**: High (UX improvement)
**Effort**: Low (2 hours)

**Current State**: No toast system
**Target**: sonner library (already installed)

**Implementation**:

Create `frontend/src/components/ui/sonner.tsx`:
```tsx
import { useTheme } from "@/components/theme-provider";
import { Toaster as Sonner } from "sonner";

export function Toaster() {
  const { resolvedTheme } = useTheme();

  return (
    <Sonner
      theme={resolvedTheme as "light" | "dark"}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast: "bg-card text-card-foreground border-border shadow-lg",
          description: "text-muted-foreground",
          actionButton: "bg-brand text-brand-foreground",
          cancelButton: "bg-muted text-muted-foreground",
        },
      }}
    />
  );
}
```

Add to `App.tsx`:
```tsx
import { Toaster } from "@/components/ui/sonner";

<ThemeProvider>
  <QueryClientProvider>
    <AuthProvider>
      <App />
      <Toaster />
    </AuthProvider>
  </QueryClientProvider>
</ThemeProvider>
```

Usage:
```tsx
import { toast } from "sonner";

toast.success("Configuration saved");
toast.error("Failed to load session");
toast.loading("Processing...");
```

**Success Criteria**:
- ✅ Toasts appear in bottom-right
- ✅ Theme-aware styling
- ✅ Accessible (live region)
- ✅ Auto-dismiss after 3s

---

### 3.2 Add Loading Spinner Component ⭐⭐
**Priority**: Medium
**Impact**: Medium (UX consistency)
**Effort**: Low (1 hour)

**Implementation**:

Create `frontend/src/components/ui/spinner.tsx`:
```tsx
import { cn } from "@/lib/utils";

export function Spinner({ className, size = "default" }: {
  className?: string;
  size?: "sm" | "default" | "lg";
}) {
  return (
    <div
      className={cn(
        "animate-spin rounded-full border-2 border-current border-t-transparent text-brand",
        {
          "h-4 w-4": size === "sm",
          "h-8 w-8": size === "default",
          "h-12 w-12": size === "lg",
        },
        className
      )}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}
```

**Usage**:
```tsx
{isLoading && <Spinner />}
<Suspense fallback={<Spinner size="lg" />}>
  <LazyView />
</Suspense>
```

---

### 3.3 Implement Form Validation Helpers ⭐⭐
**Priority**: Medium
**Impact**: Medium (developer experience)
**Effort**: Medium (3 hours)

**Goal**: Integrate react-hook-form + zod (already installed)

**Implementation**:

Create `frontend/src/components/ui/form.tsx` (shadcn pattern):
```tsx
// Form wrapper components with automatic error handling
export const Form = FormProvider;
export const FormField = Controller;
// FormItem, FormLabel, FormControl, FormDescription, FormMessage
```

Example usage:
```tsx
const formSchema = z.object({
  endpoint: z.string().url(),
  temperature: z.number().min(0).max(1),
});

function ConfigForm() {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  return (
    <Form {...form}>
      <FormField
        control={form.control}
        name="endpoint"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Endpoint</FormLabel>
            <FormControl>
              <Input {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </Form>
  );
}
```

---

### 3.4 Add Data Table Component ⭐⭐
**Priority**: Medium
**Impact**: Medium (repository list, session list)
**Effort**: High (6 hours)

**Implementation**: Use TanStack React Table (already installed)

Create `frontend/src/components/ui/data-table.tsx`:
- Sortable columns
- Filterable columns
- Pagination
- Row selection
- Virtualization for large datasets

**Use Cases**:
- Repository list in RepositoryView
- Session list in PromptWorkbenchView
- IR function list in IrView

---

### 3.5 Responsive Sidebar ⭐
**Priority**: Medium
**Impact**: Medium (mobile UX)
**Effort**: Medium (3 hours)

**Current**: Fixed 260px sidebar (not mobile-friendly)

**Target**: Collapsible sidebar with mobile drawer

**Implementation**:

Update `App.tsx`:
```tsx
<div className="main-shell">
  {/* Desktop: Fixed sidebar */}
  <aside className="hidden md:flex border-r bg-card p-6 flex-col gap-6">
    {/* ... */}
  </aside>

  {/* Mobile: Drawer */}
  <Sheet>
    <SheetTrigger asChild className="md:hidden">
      <Button variant="ghost" size="icon">
        <Menu className="h-5 w-5" />
      </Button>
    </SheetTrigger>
    <SheetContent side="left">
      {/* Same sidebar content */}
    </SheetContent>
  </Sheet>

  <main className="flex-1 p-4 md:p-8">
    {/* ... */}
  </main>
</div>
```

**Success Criteria**:
- ✅ Desktop: Sidebar visible
- ✅ Mobile: Hamburger menu opens drawer
- ✅ Drawer closes on navigation

---

### 3.6 Add Sheet Component ⭐
**Priority**: Medium
**Impact**: Medium (mobile navigation)
**Effort**: Low (1 hour)

Create `frontend/src/components/ui/sheet.tsx` using `@radix-ui/react-dialog`:
- Slides from left/right/top/bottom
- Overlay backdrop
- Close on outside click
- Keyboard accessible

---

### 3.7 Component Playground View ⭐
**Priority**: Low
**Impact**: Low (developer tool)
**Effort**: Medium (4 hours)

**Goal**: Internal page to view all components

Create `frontend/src/views/ComponentPlayground.tsx`:
- Grid of all components
- Each component with variants
- Copy code button
- Dark/light toggle
- Useful for QA and design review

---

## Quick Wins (Ongoing)
**Goal**: Small improvements, high value
**Timeline**: As needed

### QW.1 Add JSDoc to All Components ⭐
**Effort**: 2 hours total

Add comprehensive JSDoc with examples to:
- Slider
- Switch
- RadioGroup
- Checkbox
- Progress
- Skeleton

**Template**:
```tsx
/**
 * Checkbox component with indicator
 *
 * @example
 * <Checkbox id="terms" />
 * <Label htmlFor="terms">Accept terms</Label>
 */
```

---

### QW.2 Add Empty State Component ⭐
**Effort**: 1 hour

Create `frontend/src/components/ui/empty-state.tsx`:
```tsx
<EmptyState
  icon={<FileX className="h-12 w-12" />}
  title="No sessions found"
  description="Create your first session to get started"
  action={<Button>Create Session</Button>}
/>
```

Use in:
- PromptWorkbenchView (no sessions)
- RepositoryView (no repos)
- IrView (no IR)

---

### QW.3 Add Command Palette (CMD+K) ⭐⭐
**Priority**: Medium
**Effort**: 3 hours

Use `cmdk` library (already installed):
```tsx
import { Command } from "@/components/ui/command";

<Command>
  <CommandInput placeholder="Search..." />
  <CommandList>
    <CommandGroup heading="Navigation">
      <CommandItem onSelect={() => setSection("configuration")}>
        Configuration
      </CommandItem>
      {/* ... */}
    </CommandGroup>
  </CommandList>
</Command>
```

**Trigger**: CMD+K / CTRL+K
**Features**:
- Navigate to sections
- Quick theme switch
- Search sessions
- Sign out

---

### QW.4 Add Keyboard Shortcuts Help Dialog ⭐
**Effort**: 2 hours

Create `frontend/src/components/keyboard-shortcuts.tsx`:
- Shows all shortcuts (CMD+K, ESC, etc.)
- Triggered by pressing `?`
- Uses Dialog component

---

## Performance Optimizations

### PO.1 Implement Virtual Scrolling ⭐⭐
**Priority**: Medium
**Effort**: High (8 hours)

**Goal**: Handle large session/repository lists

Use `@tanstack/react-virtual`:
```tsx
import { useVirtualizer } from "@tanstack/react-virtual";

function SessionList({ sessions }) {
  const parentRef = useRef();
  const virtualizer = useVirtualizer({
    count: sessions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100,
  });

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      {virtualizer.getVirtualItems().map(item => (
        <div key={item.index}>
          <SessionCard session={sessions[item.index]} />
        </div>
      ))}
    </div>
  );
}
```

---

### PO.2 Add Image Optimization ⭐
**Priority**: Low
**Effort**: Low (1 hour)

- Use WebP format for design assets
- Add lazy loading: `loading="lazy"`
- Optimize avatar images

---

### PO.3 Implement Service Worker for Caching ⭐
**Priority**: Low
**Effort**: High (8 hours)

- Cache design system assets
- Offline-first for static content
- Cache-first strategy for fonts, images

---

## Testing Improvements

### TI.1 Fix React act() Warnings ⭐⭐
**Priority**: Medium
**Effort**: Medium (4 hours)

Wrap state updates in tests:
```tsx
await act(async () => {
  await user.click(button);
});
```

**Target**: 29/29 tests passing

---

### TI.2 Add Visual Regression Tests ⭐⭐
**Priority**: Medium
**Effort**: High (8 hours)

Use Playwright + Percy/Chromatic:
```typescript
test('component matches snapshot', async ({ page }) => {
  await page.goto('/playground');
  await expect(page).toHaveScreenshot();
});
```

**Coverage**:
- All 25 components
- Light/Dark/HC themes
- Mobile/Desktop viewports

---

### TI.3 Add Storybook ⭐
**Priority**: Low
**Effort**: High (12 hours)

Configure Storybook for:
- Component documentation
- Interactive props
- Accessibility checks
- Visual regression

---

## Documentation Improvements

### DI.1 Add Video Walkthrough ⭐⭐
**Priority**: Medium
**Effort**: Medium (3 hours)

Record Loom video:
- Design system overview (5 min)
- Component usage (10 min)
- Theme switching (3 min)
- Migration guide (7 min)

---

### DI.2 Add Figma Design Tokens ⭐
**Priority**: Low
**Effort**: Medium (4 hours)

Export tokens to Figma:
- Colors
- Typography
- Spacing
- Shadows
- Radii

---

### DI.3 Create Migration Checklist ⭐
**Priority**: Medium
**Effort**: Low (1 hour)

Create `docs/MIGRATION_CHECKLIST.md`:
- [ ] Remove inline styles
- [ ] Replace hardcoded colors
- [ ] Use semantic components
- [ ] Test keyboard navigation
- [ ] Test theme switching
- [ ] Check mobile responsiveness

---

## Summary Timeline

### Week 1 (Sprint 1): Critical Path
- Day 1-2: View migration (ConfigurationView, SignInView)
- Day 3: Skip links + accessibility
- Day 4-5: Bundle code splitting

**Outcome**: 2 views migrated, bundle optimized, accessibility improved

### Week 2 (Sprint 2): View Migration
- Day 1-2: PromptWorkbenchView, RepositoryView
- Day 3: EnhancedIrView, IdeView
- Day 4-5: PlannerView, IrView, polish

**Outcome**: All 9 views using design system, zero inline styles

### Week 3 (Sprint 3): Enhancements
- Day 1: Toast system, Spinner
- Day 2-3: Form validation, Data table
- Day 4-5: Responsive sidebar, Sheet component

**Outcome**: Enhanced UX, mobile-friendly, production-ready

### Week 4: Polish & Launch
- QA testing
- Fix remaining bugs
- Documentation updates
- Team training

---

## Success Metrics

### Before (Current State)
- ✅ 25 components
- ⚠️ 1/9 views migrated (11%)
- ⚠️ 140 inline styles
- ⚠️ 552 kB bundle
- ⚠️ No mobile optimization
- ✅ 21/29 tests passing (72%)

### After (Target State)
- ✅ 30+ components (add Sheet, Form, Spinner, Empty State, Command)
- ✅ 9/9 views migrated (100%)
- ✅ 0 inline styles
- ✅ ~300 kB main bundle (code split)
- ✅ Mobile-responsive sidebar
- ✅ 29/29 tests passing (100%)
- ✅ Toast notifications
- ✅ Form validation
- ✅ Data tables
- ✅ Command palette

---

## Resource Allocation

### Required Skills
- **Frontend Developer** (primary): React, TypeScript, Tailwind
- **Designer** (review): Color contrast, spacing, responsive
- **QA Engineer** (testing): Accessibility, cross-browser

### Estimated Hours
- **Sprint 1**: 16 hours
- **Sprint 2**: 20 hours
- **Sprint 3**: 18 hours
- **Quick Wins**: 8 hours
- **Total**: ~62 hours (~1.5 developer-weeks)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking changes during migration | Low | Medium | Thorough testing, feature flags |
| Bundle size regression | Medium | Medium | Code splitting, monitoring |
| Theme bugs | Low | Low | Manual QA in all themes |
| Mobile issues | Medium | High | Real device testing |
| Performance degradation | Low | Medium | Lighthouse monitoring |

---

## Conclusion

This improvement plan transforms the design system from **good** to **excellent**:

1. **Complete migration** - All views use design system
2. **Optimized performance** - Code splitting, lazy loading
3. **Enhanced UX** - Toasts, forms, data tables, command palette
4. **Mobile-first** - Responsive sidebar, drawer navigation
5. **Production-ready** - 100% test coverage, visual regression tests

**Recommended Approach**: Execute sprints sequentially, starting with Sprint 1's critical path.

---

**Plan Version**: 1.0
**Author**: Design System Team
**Review Status**: Ready for approval
**Next Step**: Sprint 1 kickoff
