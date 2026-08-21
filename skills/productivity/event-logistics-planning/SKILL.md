---
name: event-logistics-planning
description: Use when planning live event routes and access.
version: 1.0.0
author: Skibidi / Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [events, logistics, maps, routing, travel, planning]
    related_skills: [agent-reach, maps]
---

# Event Logistics Planning

## Overview

Use this skill when the user needs practical help attending, watching, parking for, or navigating a live event whose routes, closures, access rules, or timing may change. The goal is not a generic travel summary; the goal is a usable field plan grounded in official updates, maps, and realistic access tradeoffs.

Typical examples: parades, concours/tours, races, festivals, evacuations/reroutes, road-closure events, venue ingress/egress, viewing spots, parking plans, and Plan A/B/C timing.

## When to Use

Use when the user asks for:

- Where to watch a moving event after a route change.
- Parking/access/timing plans for an event.
- Reroute interpretation from an official map/PDF.
- Best viewing spots with pros/cons.
- A concise practical itinerary for arriving, staging, and falling back if access is blocked.

Do not use for pure vacation ideation with no event constraint; use general maps/travel tools instead.

## Workflow

1. **Official source first.** Find the event organizer’s update page, route map, venue page, or municipal/agency closure notice before relying on search snippets or social posts. Completion: quote or summarize the official date/time/route/access facts and provide the source link.

2. **Resolve event identity and date.** Check whether similarly named events happen on different days. If the user says “Sunday” but the official route map says another date, state the mismatch clearly and non-judgmentally. Completion: final answer distinguishes the event being planned from adjacent/ticketed events.

3. **Extract route/access facts.** For maps/PDFs/images, identify start/finish, wave times, named roads, one-way direction, route loops, public-viewing invitations, and restricted/closure notes. Completion: produce a short route fact block.

4. **Convert map into watch/arrival options.** Recommend 3-5 spots ranked by reliability:
   - guaranteed/high-certainty official start/finish
   - scenic/photo spot
   - lower-crowd interior/secondary spot
   - fallback with better public parking/access
   For each, include timing, why it works, tradeoff, and a map link.

5. **Do not encourage chasing.** For moving car/race/parade routes, warn against trying to chase the route unless official shuttle/access supports it. Traffic controls usually beat spectators. Completion: recommend picking one spot or one fallback transition.

6. **Plan A/B/C.** End with a practical plan: arrival target, primary spot, fallback trigger, secondary spot, and what to verify day-of. Completion: user can act without asking “so where exactly should I go?”

## Output Shape

```markdown
## Quick read
**Best Pick**: ...
**Backup**: ...
**Arrive By**: ...
**Source Check**: official page/map says ...

## Spots
**1. Spot Name — safest/best/etc.**
**Why**: ...
**Best Time**: ...
**Tradeoff**: ...
**Map**: ...

## Plan
**Plan A**: ...
**Plan B**: ...
**Avoid**: ...
```

## References

- `references/pebble-beach-tour-delegance-2026.md` — example of turning an official reroute update/PDF into practical watch spots, timing, and fallback plans.

## Common Pitfalls

1. **Using stale route assumptions.** Always re-check official updates for reroutes, fires, closures, police instructions, and start times.
2. **Missing date mismatch.** Event-week tickets may be for a different day than the route/tour/parade. State the mismatch.
3. **Over-optimizing for scenery.** The prettiest spot may be inaccessible; rank reliability first unless the user explicitly wants photography.
4. **No parking reality.** A viewing recommendation without parking/access tradeoffs is incomplete.
5. **Route-chasing advice.** Do not suggest chasing a moving event through controlled roads unless official logistics permit it.

## Verification Checklist

- [ ] Official source checked.
- [ ] Event date/time and user’s stated date reconciled.
- [ ] Route/start/finish facts extracted.
- [ ] Watch spots ranked by reliability and use case.
- [ ] Map links included where possible.
- [ ] Arrival timing and fallback plan provided.
