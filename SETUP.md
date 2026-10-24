# Setup: running this project with AI agents

## How it works

The agents run in parallel as separate GitHub Actions workflows and talk to each other
through GitHub Issues, labels and PRs (the "task board", see CLAUDE.md):

```
 Mon/Wed/Fri       agent-research.yml          agent-proposal-review.yml       agent-plan.yml
 ──────────▶ strategy-researcher ──issue──▶ quant-reviewer ──approved──▶ planner ──task issues──┐
             (papers, news → 1 proposal)    (APPROVE / REJECT)            (also daily, and on    │
                                                                           `needs-planning`)     │
   ┌─────────────────────────────────────────────────────────────────────────────────────────┘
   ▼  agent-work.yml (every 4h, on every merge to main, and when the planner adds tasks)
 backend-engineer ┐
 frontend-engineer├─ in parallel, one open PR per role ──▶ PR ──▶ agent-review.yml ──▶ YOU merge
 strategy-research┘                                            (code + quant review,     │
                                                                1 fix round; follow-ups  │
                                                                → `needs-planning`)      │
        ▲                                                                                │
        └──────────────── merge closes the task issue and unblocks the next ◀────────────┘
```

| Workflow | Agent | Runs when |
|---|---|---|
| `agent-research.yml` | strategy-researcher | Mon/Wed/Fri, if fewer than 3 proposals are waiting |
| `agent-proposal-review.yml` | quant-reviewer (Opus) | a `proposal` issue is opened |
| `agent-plan.yml` | planner | a proposal is approved, an issue is labelled `needs-planning`, daily |
| `agent-work.yml` | backend / frontend / strategy (one job each) | every 4h, on merge to `main`, after planning |
| `agent-review.yml` | code-reviewer + quant-reviewer | an agent PR is opened or updated |

- **You** own `docs/GOAL.md`, the workflows and the merge button. Agents own everything
  else through issues and PRs. Steer by editing/closing issues, or by opening an issue
  labelled `needs-planning` describing what you want.

---

## Step 1 — Install the tools (once)

1. **VS Code**, **Git**, **Python 3.12** and **Node.js 20+**.
2. **GitHub CLI** (https://cli.github.com), then run `gh auth login`.
3. **Claude Code extension for VS Code:** search "Claude Code" in the Extensions panel and
   install the one published by Anthropic. Sign in with your Claude subscription (Pro/Max)
   or a Claude Console account. Docs: https://code.claude.com/docs/en/vs-code
4. Optional but recommended: the Claude Code CLI too, so you can run `claude` in the
   terminal. Setup docs: https://code.claude.com/docs/en/setup

## Step 2 — Create the repo

1. On GitHub, create a **private** repo, e.g. `paper-trading`, with no README.
2. In VS Code: Command Palette → "Git: Clone" → pick the repo → open it.
3. Unzip this skeleton and copy its contents (including the hidden `.claude/`, `.github/`,
   `.gitignore`, `.env.example`) into the repo folder.
4. Fill in the `<!-- fill in -->` parts of `docs/GOAL.md`.
5. Commit and push to `main`:
   ```bash
   git add -A && git commit -m "chore: project skeleton" && git push
   ```

## Step 3 — Build the first milestones with you watching (local)

Open the Claude Code panel in VS Code (the Claude icon in the sidebar) and send:

> Act as the orchestrator described in CLAUDE.md. Pick the next `todo` task in
> docs/PLAN.md, delegate it to the right subagent, and open a PR.

You'll see every step live in the panel: files read, commands run, and each subagent call.
Review the PR on GitHub, merge it, and repeat. Do M0 (and ideally M1–M2) this way. Each time
an agent makes the same mistake twice, add a rule to CLAUDE.md.

## Step 4 — Turn on the automation (GitHub)

1. **Claude GitHub app + auth secret:** in the Claude Code CLI inside the repo, run
   `/install-github-app` and follow the prompts. It installs the app and adds either
   `CLAUDE_CODE_OAUTH_TOKEN` (uses your Pro/Max subscription) or `ANTHROPIC_API_KEY`
   (billed per token). It also offers its own workflow files; the `@claude` one is handy
   (comment `@claude please fix X` on any PR). Manual route:
   https://code.claude.com/docs/en/github-actions#manual-setup
2. **Agent token:** create a fine-grained personal access token (GitHub → Settings →
   Developer settings) for this repo only, with Contents, Pull requests and Issues set to
   read/write, and **Actions** read/write (lets the planner start the workers right
   away). Save it as the repo secret `AGENT_GH_TOKEN`. Without it, issues and PRs opened
   by agents won't trigger the next agent's workflow.
3. **Labels:**
   ```bash
   for l in agent ready-for-human needs-human fix-round-1 question             task role:backend role:frontend role:strategy             status:todo status:in-progress status:in-review status:blocked             proposal proposal-approved proposal-rejected planned needs-planning             milestone:M1 milestone:M2 milestone:M3 milestone:M4 milestone:M5 milestone:M6 milestone:M7; do
     gh label create "$l" --force
   done
   ```
4. **Protect main:** Settings → Branches → add a rule for `main`: require a pull request,
   require the `checks` status check, block force pushes.
5. **Test it:** Actions tab → `agent-plan` → "Run workflow". The planner creates the M1
   task issues and then starts `agent-work`. To start the research loop right away, also
   run `agent-research`. Watch any run live by clicking it, then its job.

## Where to watch the agents

| What | Where |
|---|---|
| Local runs, live | Claude Code panel in VS Code |
| Automated runs, live | GitHub → Actions tab → click the run → expand the Claude step |
| Reviews and verdicts | Comments on each PR |
| What needs you | PRs filtered by label `ready-for-human` or `needs-human` |
| Overall progress | Issues tab, filter `label:task` (group by `status:*`) |
| Strategy ideas and verdicts | Issues tab, filter `label:proposal` (open and closed) |

## Your daily loop (about 10 minutes)

1. Open PRs labelled `ready-for-human` or `needs-human`.
2. Read the reviewers' summaries, then the diff. For strategy PRs, open the backtest report.
3. Merge, comment `@claude <what to change>`, or close.
4. Skim new `proposal` issues and the quant-reviewer's verdicts. To overrule a verdict,
   change the label (`proposal-approved` starts planning).
5. Skim new `task` issues from the planner; edit or close any you disagree with.

## Cost controls already in place

One open agent PR per role (max 3 at once), at most 3 waiting proposals, research three
times a week, workers that exit before calling Claude when no task is ready, one fix
round, turn caps, Sonnet everywhere except the quant-reviewer (Opus). The worker
schedule (`17 */4 * * *` in `agent-work.yml`) is the main cost dial. Set a monthly spend limit in the Anthropic Console if you use an API key.
GitHub Actions minutes are separate (private repos get a free monthly allowance).

## Troubleshooting

- **Claude can't run commands in Actions:** add the command to `--allowedTools` in the
  workflow.
- **Review didn't start on an agent PR:** check `AGENT_GH_TOKEN` is set and the PR has the
  `agent` label.
- **Scheduled run never fires:** schedules only run from `main`; check the Actions tab is
  enabled.
- More: https://code.claude.com/docs/en/github-actions#troubleshooting
