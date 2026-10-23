# Setup: running this project with AI agents

## How it works

```
 once/day            agent-work.yml                     agent-review.yml (on PR)
 ─────────▶  orchestrator reads PLAN.md ──▶ subagent ──▶ PR ──▶ CI ──▶ code-reviewer
                                                                        quant-reviewer
                                                        ▲                    │
                                                        └── fixes (max 1) ◀──┘
                                                                             │
                                                     label: ready-for-human / needs-human
                                                                             ▼
                                                                    YOU review + merge
```

- **Orchestrator:** the main Claude session. In GitHub it's the prompt in
  `agent-work.yml`; locally it's the Claude Code chat you're talking to. It reads the plan
  and delegates to the subagents in `.claude/agents/`.
- **You** own `docs/GOAL.md`, the workflows and the merge button. Agents own everything
  else through PRs.

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
   read/write. Save it as the repo secret `AGENT_GH_TOKEN`. Without it, PRs opened by the
   worker won't trigger the review workflow.
3. **Labels:**
   ```bash
   for l in agent ready-for-human needs-human fix-round-1 question; do gh label create "$l"; done
   ```
4. **Protect main:** Settings → Branches → add a rule for `main`: require a pull request,
   require the `checks` status check, block force pushes.
5. **Test it:** Actions tab → `agent-work` → "Run workflow". Watch it live by clicking the
   run, then the `work` job.

## Where to watch the agents

| What | Where |
|---|---|
| Local runs, live | Claude Code panel in VS Code |
| Automated runs, live | GitHub → Actions tab → click the run → expand the Claude step |
| Reviews and verdicts | Comments on each PR |
| What needs you | PRs filtered by label `ready-for-human` or `needs-human` |
| Overall progress | Task statuses in `docs/PLAN.md` |

## Your daily loop (about 10 minutes)

1. Open PRs labelled `ready-for-human` or `needs-human`.
2. Read the reviewers' summaries, then the diff. For strategy PRs, open the backtest report.
3. Merge, comment `@claude <what to change>`, or close.
4. At the start of each milestone, merge (or edit) the planner's `plan:` PR; this is where
   you steer.

## Cost controls already in place

One task per day, one open agent PR at a time, one fix round, turn caps, and Sonnet as the
default model. Set a monthly spend limit in the Anthropic Console if you use an API key.
GitHub Actions minutes are separate (private repos get a free monthly allowance).

## Troubleshooting

- **Claude can't run commands in Actions:** add the command to `--allowedTools` in the
  workflow.
- **Review didn't start on an agent PR:** check `AGENT_GH_TOKEN` is set and the PR has the
  `agent` label.
- **Scheduled run never fires:** schedules only run from `main`; check the Actions tab is
  enabled.
- More: https://code.claude.com/docs/en/github-actions#troubleshooting
