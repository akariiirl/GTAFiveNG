# Instructions for future Codex sessions

Read PROJECT_STATUS.md, ARCHITECTURE.md and BUILD.md before changing the project. Existing historical documents describe older milestones; prefer the dated status and inspect current code and local evidence when they differ.

- Preserve existing user changes, local generated outputs and all build checkpoints. Never overwrite a working build, game installation or normal BeamNG profile. Use new output directories and ZIP names.
- GTA V and BeamNG assets are proprietary. Keep game files, exports, textures, generated levels, packages and keys out of Git and remote services, including private repositories and cloud workspaces. Do not upload them without explicit user authorization and appropriate rights.
- The user has a limited project credit budget. Work efficiently, use focused checks, and avoid unnecessary broad conversion, cloud setup, agents or repeated testing.
- Do not push or create a remote repository without user approval. Before staging, inspect `git status` and `git diff`, and verify staged filenames and contents for proprietary data and secrets. Git ignore rules are safeguards, not a substitute for review.
- After each major milestone update PROJECT_STATUS.md with date, exact evidence, limitations, blockers and next steps; update BUILD.md or ARCHITECTURE.md when their facts change. Do not claim a drive, visual or performance test without evidence.
- Do not unnecessarily alter the conversion pipeline. Keep source access read-only and respect LICENSES.md. Treat existing machine paths and ignored local dependencies as examples, not portable defaults.

## Standing user authorization — 2026-11-16

The user explicitly authorizes routine development, testing, committing, pushing,
and clean PR merges in akariiirl/GTAFiveNG. For each completed milestone: branch
from updated master, test, review staged source for licensed data/secrets, push,
open a PR targeting master, wait for **all** CI checks/review requirements, merge
only when passing and permitted, verify the merge, then update from master and
continue. Never bypass protections, failing/pending checks or security review.
If blocked, record the exact blocker and continue independent authorized work.
Do not leave passing completed PRs open unnecessarily. This standing authorization
satisfies the earlier requirement to obtain user approval before pushing.

Latest user budget (final cloud preparation): 380 credits remaining out of 500,
120 spent, preserve 320 for local GTA V/BeamNG work, target at most 60 additional
cloud credits. These supersede earlier balance/allocation statements. This is a
planning target, not a metered cap. Tools expose no live usage; never invent credit
consumption or claim to enforce it. Keep milestones small and avoid uncertain work.
Never access local installations/desktops or upload proprietary assets in cloud.
