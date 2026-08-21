---
name: open-design
description: Design and build stunning, production-grade web UIs, dashboards, and user-facing components using the Open Design (nexu-io/open-design) design system contract. Trigger whenever building, styling, or refactoring dashboard pages, UI widgets, modals, charts, or visual interfaces.
---

# Open Design Skill (`open-design`)

This skill enables AI agents to function as a specialized **Vibe Design Engine**, building visually stunning, local-first web dashboards and component interfaces.

---

## 🚀 Workflow Instructions

When invoked to build, style, or refactor any user-facing UI component or dashboard page:

### 1. Read the Design System Contract (`web/DESIGN.md`)
Always check `web/DESIGN.md` in the current project repository. It contains the exact color tokens, typography rules, glassmorphism settings, and interaction patterns.

### 2. Follow Open Design Principles
- **No Generic Default Styling**: Never output plain white backgrounds, basic unstyled tables, or default browser buttons.
- **Dark Mode Glassmorphism First**: Use `#0B0F17` obsidian base background, `#131924` elevated glass cards with `backdrop-blur-xl`, and subtle border glows (`border-indigo-500/20`).
- **Dynamic Numeric Data Layouts**: Format all quantitative values, prices, percentages, and metrics using bold monospace typography (`font-mono font-bold`).
- **Tactical Visual Feedback**: Add glowing pulse indicators (`animate-pulse`), status pill badges, and active micro-animations (`active:scale-95 transition-all`).

### 3. Component Patterns
- **KPI Summary Cards**: 3-column grid featuring large value displays, progress fill bars, and upper-right icon badges.
- **Real-Time Data Tables**: Sticky glass headers, subtle row hover states, and monospace aligned data columns.
- **Interactive Calculation Widgets**: Clean compact form fields with inline real-time formula output preview.

### 4. Code Quality & Responsiveness
- Write clean, type-safe React (TypeScript) and Vanilla CSS / Tailwind classes.
- Ensure all components are responsive (`grid-cols-1 md:grid-cols-3`).
- Include descriptive `id` and `aria-label` tags on interactive elements for accessibility and automated testing.
