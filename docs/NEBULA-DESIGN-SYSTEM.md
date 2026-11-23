# Nebula Command — Design 1

## Intent

Nebula Command is the mobile-first control surface for OpenHands Devbox. It uses a deep-space navy foundation, cyan primary actions, violet secondary accents, restrained glow-like emphasis, high-contrast text, and compact operational cards.

## Implemented in this change

- Replaces the previous orange/brown Material palette with the Nebula dark token set.
- Adds a Dashboard as the app's initial screen.
- Adds live app-state labels sourced from the existing ViewModel (busy, statusText, selected project, profile, and configured model).
- Adds direct navigation from the dashboard to Chat, Projects, Settings, and Live Preview.
- Adds a return path from Chat to the Dashboard.

## Existing capabilities retained

The UI continues to use the current GitHub Actions workflow and Android ViewModel for actual task execution. The existing Superagent profiles, project selection, encrypted GitHub token storage, auto-merge controls, attachments, live preview, project memory, Free Route Hunter and LLM Autopilot workflows, MCP/Skills setup, and quality-gate scripts remain the execution layer.

## Truthful status rules

- busy and statusText are the app's current workflow state; they are not a fabricated agent heartbeat.
- An empty model setting means the workflow is configured to run Free Route Hunter before agent execution. It does not mean a free model is currently online.
- A configured model is shown as configured, not as health-checked.
- Live Preview opens the configured URL; it does not imply that the remote app passed a health check.
- Agent, route, MCP, and CI health indicators must be driven by real API/workflow results before being displayed as green.

## Follow-up implementation areas

1. Add dedicated route-health and LLM Autopilot screens backed by the existing workflow reports.
2. Add a Project Memory view backed by projects/<slug>/GEDAEHNTNIS.md and the existing memory scripts.
3. Add a Tool Packs/MCP inventory backed by the repository's pack catalog and actual Canvas configuration.
4. Add run history, quality-gate reports, and PR review state backed by GitHub Actions and Pull Request APIs.
5. Extend responsive navigation and accessibility testing across Android phone and tablet sizes.

## Validation

This PR changes the Android Compose UI and theme. CI must run the existing Android build and unit tests. A successful GitHub commit or PR creation is not evidence that the APK builds; report the actual Actions result separately.