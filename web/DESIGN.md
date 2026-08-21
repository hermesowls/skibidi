# Open Design System Specification (web/DESIGN.md)

> Portable Vibe Design System Contract for Dashboard Interfaces & UI Components

---

## 1. 🎨 Color Tokens & Palette Hierarchy

### Core Backgrounds & Surfaces
- **Background Base (`bg-base`)**: Deep Cyber Obsidian — `#0B0F17`
- **Elevated Card Surface (`bg-card`)**: Dark Slate Glass — `#131924` (80%–90% opacity with `backdrop-blur-xl`)
- **Interactive Hover Surface**: `#1C2433`
- **Borders & Dividers**: `border-indigo-500/20` (featured) or `border-slate-800/80` (subtle)

### Signal Accent Tokens
- 🟢 **Success / Bullish / Profit**: Cyberpunk Emerald (`#10B981`, `bg-emerald-500/10`, `text-emerald-400`, `border-emerald-500/30`)
- 🔵 **Info / Neutral Momentum**: Neon Cyan (`#06B6D4`, `bg-cyan-500/10`, `text-cyan-400`, `border-cyan-500/30`)
- 🟣 **GEX / Volatility / Attractor**: Royal Purple (`#8B5CF6`, `bg-purple-500/10`, `text-purple-400`, `border-purple-500/30`)
- 🟡 **Warning / Stand Aside**: Gold Amber (`#F59E0B`, `bg-amber-500/10`, `text-amber-400`, `border-amber-500/30`)
- 🔴 **Risk / Bearish / Stop**: Rose Red (`#F43F5E`, `bg-rose-500/10`, `text-rose-400`, `border-rose-500/30`)

---

## 2. 💎 Surface & Glassmorphism Rules

1. **Backdrop Blur**: Every card, modal overlay, and navigation header must include `backdrop-blur-xl`.
2. **Hero Header Gradient**: `bg-gradient-to-r from-indigo-950/60 via-purple-950/40 to-slate-900/80 border border-indigo-500/20`.
3. **Elevated Card Glow**: Drop shadow with subtle colored ambient glow: `shadow-2xl shadow-indigo-950/50 hover:shadow-indigo-500/10 transition-all`.
4. **Rounded Boundaries**: Containers use `rounded-2xl` (16px) or `rounded-xl` (12px). Badges use `rounded-full`.

---

## 3. 🔤 Typography & Metrics Standard

- **Quantitative Values & Financial Data**: Always render numbers in Monospace (`font-mono font-bold text-slate-100`).
- **Section Headers**: Uppercase, tracked small headers (`text-xs font-bold uppercase tracking-wider text-slate-400`).
- **Hero Title**: Gradient fill typography:
  ```html
  <h1 className="text-3xl font-black tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-indigo-200">
    Title Text
  </h1>
  ```
- **Fonts**: Inter / Outfit for prose and UI sans-serif; Fira Code / JetBrains Mono for numeric tabular data.

---

## 4. ⚡ Micro-Interactions & Components

### A. Live Status Dot
```html
<span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
  Live System Connected
</span>
```

### B. Tactical Action Badge
```html
<span className="px-3 py-1 rounded-full text-xs font-black border shadow-md bg-emerald-500/20 text-emerald-300 border-emerald-500/40">
  🚀 BUY BREAKOUT
</span>
```

### C. Interactive Button
```html
<button className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600/80 hover:bg-indigo-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/25 border border-indigo-400/30 active:scale-95">
  Action Button
</button>
```

---

## 5. 🛠️ Layout & Responsiveness Guidelines

- Use **CSS Grid / Flexbox** with explicit gaps (`gap-4`, `gap-6`).
- Grid structure: `grid-cols-1 md:grid-cols-3` or `grid-cols-1 lg:grid-cols-4`.
- Never hardcode static pixel widths for main layout containers; use fluid percentages or CSS flex flex-grow.
- Table design: Sticky headers (`sticky top-0 bg-[#0B0F17]`), subtle row borders (`border-b border-slate-800/60`), and hover highlight (`hover:bg-slate-800/40`).
