# Daily Ops Workflow

This workflow produces a daily operations note by aggregating mail, calendar, tasks, and notes, then synthesizing them against goals and history.

---

## Steps

### Step 1: Delegate data gathering
Delegate to specialist agents. Use **separate delegate calls** for each:
- **mail** agent — gather inbox summary
- **calendar** agent — gather events (today + next 48h)
- **tasks** agent — gather open/overdue tasks
- **notes** agent — gather notes and open loops

### Step 2: Read goals
Read `goals/goals.md` using read_file. Use these goals to align the Direction section.

### Step 3: Read yesterday's output (dedup)
Read `history/2026-02-12.md` using read_file. This is used for:
- **Deduplication** — remove items already in yesterday's note that haven't changed
- **Escalation** — items that appeared yesterday and weren't done get escalated (increase priority, add to Escalated section with day count)

### Step 4: Read preferences
Read `memory/preferences.md` using read_file for output format, communication style, and priority rules.

### Step 5: Filter
- Remove items already in yesterday's note (no new info)
- Escalate repeated items — if something was in yesterday's Action Items or Escalated and is still open, add to Escalated with (Nd) where N = days since first appearance
- Apply priority rules from preferences (overdue first, 2+ day skip = escalate)

### Step 6: Synthesize
Compose a daily ops note with these sections (in order):
1. **Direction** — aligned with goals, what to focus on today
2. **Escalated** — overdue + items skipped 2+ days, with (Nd) suffix
3. **Shifted** — cancelled events, rescheduled meetings, calendar changes
4. **Action Items** — prioritized list with checkboxes
5. **Protection** — any guardrails (e.g. no meetings before 12:00)

### Step 7: Write output
Write the final note to `output/YYYY-MM-DD.md` using the write_file tool. Use today's date (e.g. `2026-02-13.md`).

**IMPORTANT**: All file paths for read_file and write_file are relative to the workspace root. Do NOT include a `workspace/` prefix.

---

## Output Template

```markdown
# Daily Ops — YYYY-MM-DD (DayOfWeek)

## Direction
[1-2 sentences: focus for today, aligned with goals]

## Escalated
- **[item] (Nd)** — [brief context]. [Action needed].

## Shifted
- [Cancelled/rescheduled events and changes]

## Action Items
- [ ] [Highest priority — overdue first]
- [ ] [Due today]
- [ ] [Blocked — note blocker]
- [ ] [Upcoming]

## Protection
[Guardrails, e.g. no meetings before 12:00]
```
