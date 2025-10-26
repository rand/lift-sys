# Frontend Design System

**Hex + v0 Inspired** | **shadcn/ui Components** | **Tailwind CSS v3**

This document describes the design system powering the lift-sys frontend, built with shadcn/ui components and inspired by the visual aesthetics of Hex and v0.

---

## Table of Contents

- [Design Principles](#design-principles)
- [Color System](#color-system)
- [Typography](#typography)
- [Spacing & Layout](#spacing--layout)
- [Components](#components)
- [Theming](#theming)
- [Accessibility](#accessibility)
- [Usage Guidelines](#usage-guidelines)

---

## Design Principles

### Visual Style

- **Crisp Neutrals**: Zinc-like scale with low-chroma surfaces
- **Clear Elevation**: Subtle shadows define depth and hierarchy
- **Generous Whitespace**: Breathing room for content clarity
- **Soft Geometry**: ~1rem border radius, glassy overlays at ~10% opacity
- **Tasteful Motion**: 150–250ms transitions with smooth easing

### Component Philosophy

- **Composable**: Components build on smaller primitives
- **Accessible**: WCAG 2.1 AA compliant with proper ARIA attributes
- **Themeable**: Supports light, dark, and high-contrast modes
- **Tree-shakable**: Import only what you use
- **Type-safe**: Full TypeScript support with exported types

---

## Color System

### Token Structure

Colors are defined as HSL CSS variables for maximum flexibility:

```css
--background: 240 10% 3.9%;     /* Main background */
--foreground: 0 0% 98%;         /* Main text */
--card: 240 10% 7%;             /* Card backgrounds */
--muted: 240 3.7% 15.9%;        /* Muted backgrounds */
--border: 240 3.7% 15.9%;       /* Border colors */
```

### Brand Colors (Cyan-Emerald Spectrum)

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--brand` | `189 94% 43%` | `189 94% 53%` | Primary CTAs, focus states |
| `--accent` | `142 76% 36%` | `142 76% 46%` | Accent elements, highlights |
| `--success` | `142 76% 36%` | `142 76% 46%` | Success states, confirmations |
| `--warning` | `38 92% 50%` | `38 92% 50%` | Warnings, cautions |
| `--destructive` | `0 84.2% 60.2%` | `0 62.8% 30.6%` | Errors, destructive actions |
| `--info` | `189 94% 43%` | `189 94% 53%` | Informational elements |

### Semantic Colors

- **Primary**: Brand cyan for main actions
- **Secondary**: Muted zinc for secondary actions
- **Destructive**: Balanced red for dangerous actions
- **Success**: Emerald for positive feedback
- **Warning**: Amber for caution
- **Info**: Cyan for informational content

---

## Typography

### Font Stack

```css
font-family: 'Inter', system-ui, -apple-system, sans-serif;
```

### Font Weights

- **Regular (400)**: Body text
- **Medium (500)**: Emphasized text
- **Semibold (600)**: Headings, labels, buttons
- **Bold (700)**: Major headings

### Scale

- `text-xs`: 0.75rem / 12px
- `text-sm`: 0.875rem / 14px
- `text-base`: 1rem / 16px
- `text-lg`: 1.125rem / 18px
- `text-xl`: 1.25rem / 20px
- `text-2xl`: 1.5rem / 24px

---

## Spacing & Layout

### Radius

- `--radius`: 1rem (16px) - Base radius
- `rounded-lg`: `var(--radius)` - Cards, buttons, inputs
- `rounded-md`: `calc(var(--radius) - 0.25rem)` - Smaller elements
- `rounded-sm`: `calc(var(--radius) - 0.5rem)` - Tiny elements

### Shadows

```css
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
--shadow-brand: 0 0 0 3px hsl(189 94% 43% / 0.1);
```

### Motion

```css
--duration-fast: 150ms;
--duration-normal: 200ms;
--duration-slow: 250ms;
--ease-smooth: cubic-bezier(0.2, 0.8, 0.2, 1);
```

**Respects `prefers-reduced-motion`**: Animations reduce to near-instant when user prefers reduced motion.

---

## Components

### Core Primitives

#### Button

Multiple variants for different contexts:

```tsx
import { Button } from "@/components/ui/button";

<Button variant="default">Primary Action</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="outline">Outlined</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Delete</Button>
<Button variant="success">Confirm</Button>
<Button variant="warning">Caution</Button>
<Button variant="info">Info</Button>
```

**Sizes**: `sm`, `default`, `lg`, `icon`

#### Badge

Status indicators and labels:

```tsx
import { Badge } from "@/components/ui/badge";

<Badge variant="default">Default</Badge>
<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="destructive">Error</Badge>
```

#### Card

Flexible container with composable sections:

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description text</CardDescription>
  </CardHeader>
  <CardContent>
    Main content goes here
  </CardContent>
  <CardFooter>
    Footer actions
  </CardFooter>
</Card>
```

### Form Components

- **Input**: Text inputs with focus rings
- **Textarea**: Multi-line text input
- **Label**: Accessible form labels
- **Select**: Dropdown select with Radix primitives
- **Checkbox**: Toggle checkboxes
- **RadioGroup**: Radio button groups
- **Switch**: Toggle switches
- **Slider**: Range sliders

### Overlay Components

- **Dialog**: Modal dialogs with backdrop
- **Popover**: Floating content containers
- **Tooltip**: Accessible hover tooltips
- **DropdownMenu**: Context menus and dropdowns
- **Tabs**: Tabbed interfaces
- **Accordion**: Collapsible content

### Feedback Components

- **Alert**: Contextual alerts (4 variants)
- **Progress**: Progress bars
- **Skeleton**: Loading state placeholders
- **Avatar**: User avatars with fallbacks

### Layout & Navigation

- **Table**: Semantic table components
- **Breadcrumb**: Navigation breadcrumbs
- **Pagination**: Page navigation
- **Separator**: Visual dividers

---

## Theming

### Three Built-in Themes

#### 1. Light Mode (`:root`)
- High contrast for daylight use
- Soft shadows and subtle borders
- Warm neutral backgrounds

#### 2. Dark Mode (`.dark`)
- Default theme for lift-sys
- Reduced eye strain in low light
- Deeper shadows and brighter accents

#### 3. High Contrast (`.hc`)
- Maximum accessibility
- Pure black borders
- WCAG AAA contrast ratios

### Theme Switching

```tsx
import { ModeToggle } from "@/components/mode-toggle";
import { useTheme } from "@/components/theme-provider";

// In your app:
<ModeToggle />

// Programmatically:
const { theme, setTheme } = useTheme();
setTheme("dark"); // "light", "dark", "hc", or "system"
```

### Theme Persistence

Theme preference is saved to `localStorage` under key `vite-ui-theme`.

---

## Accessibility

### WCAG 2.1 AA Compliance

#### Color Contrast

| Pairing | Ratio | Status |
|---------|-------|--------|
| `--foreground` on `--background` | 16.5:1 | ✅ AAA |
| `--brand-foreground` on `--brand` | 7.2:1 | ✅ AA |
| `--muted-foreground` on `--background` | 4.8:1 | ✅ AA |
| `--destructive-foreground` on `--destructive` | 5.1:1 | ✅ AA |

High Contrast mode achieves **AAA** ratios for all pairings.

#### Keyboard Navigation

- All interactive components support keyboard navigation
- Focus visible with `ring-2 ring-ring ring-offset-2`
- Skip links for main content areas
- Proper ARIA attributes on all components

#### Screen Reader Support

- Semantic HTML elements
- ARIA labels on icon-only buttons
- `aria-describedby` for form errors
- Live regions for dynamic updates

### Reduced Motion

All animations respect `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Usage Guidelines

### Do's ✅

- **Use semantic variants**: `variant="destructive"` for dangerous actions
- **Compose components**: Build complex UIs from simple primitives
- **Leverage theming**: Use theme tokens instead of hardcoded colors
- **Maintain consistency**: Use the design system for all new features
- **Test accessibility**: Verify keyboard nav and screen reader support

### Don'ts ❌

- **Don't use inline styles**: Use Tailwind classes or theme tokens
- **Don't hardcode colors**: Always use CSS variables
- **Don't skip focus states**: All interactive elements need visible focus
- **Don't break responsive**: Test mobile layouts
- **Don't ignore motion preferences**: Respect `prefers-reduced-motion`

### Component Selection Guide

| Need | Component |
|------|-----------|
| Primary action | `Button variant="default"` |
| Dangerous action | `Button variant="destructive"` |
| Status label | `Badge` |
| Grouped content | `Card` |
| User confirmation | `Dialog` |
| Quick info | `Tooltip` |
| Context actions | `DropdownMenu` |
| Tabbed content | `Tabs` |
| Collapsible FAQ | `Accordion` |
| Data display | `Table` |
| Form input | `Input`, `Textarea`, `Select` |

### Example: Building a Settings Form

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function SettingsForm() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Account Settings</CardTitle>
        <CardDescription>Manage your account preferences</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" placeholder="you@example.com" />
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>Email Notifications</Label>
            <p className="text-sm text-muted-foreground">
              Receive updates about your account
            </p>
          </div>
          <Switch />
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="default">Save Changes</Button>
      </CardFooter>
    </Card>
  );
}
```

---

## Migration Guide

### From Old Components to New

#### Button Migration

**Before:**
```tsx
<button style={{ background: "#6366f1", padding: "0.6rem 1rem" }}>
  Click me
</button>
```

**After:**
```tsx
import { Button } from "@/components/ui/button";

<Button>Click me</Button>
```

#### Card Migration

**Before:**
```tsx
<div style={{ background: "#1e293b", borderRadius: "1rem", padding: "1.5rem" }}>
  <h2>Title</h2>
  Content
</div>
```

**After:**
```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>Content</CardContent>
</Card>
```

---

## Resources

- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Radix UI Primitives](https://www.radix-ui.com)
- [Tailwind CSS](https://tailwindcss.com)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Last Updated**: October 2025
**Maintainer**: lift-sys Team
