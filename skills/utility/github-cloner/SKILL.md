---
name: github-cloner
description: Clone, install, or update GitHub repositories sent via Telegram, Discord, CLI, or TUI into dedicated isolated directories with automatic dependency installation.
---

# GitHub Repository Cloner Skill

Use this skill whenever requested via **Telegram**, **Discord**, **CLI**, or **TUI** to clone, install, or update a GitHub repository (e.g., "clone https://github.com/owner/repo", "install repo owner/repo", "clone skill https://github.com/owner/repo").

---

## ⚡ Execution Rules & Target Routing

| Target Type | Destination Path | Usage |
| :--- | :--- | :--- |
| **External Repo (Default)** | `~/.hermes/repos/<repo-name>` | General GitHub tools, scripts, Python projects |
| **Hermes Plugin** | `~/.hermes/plugins/<repo-name>` | Hermes gateway/dashboard plugins |
| **Hermes Skill** | `~/.hermes/skills/<repo-name>` | Skill packages containing `SKILL.md` |

---

## ⛔ FORMATTING LAWS (TELEGRAM & DISCORD)

> [!CAUTION]
> 1. **BAN ON BULLET POINTS (`•`, `-`, `*`)**: Format all output lines with bold label prefixes: `**Repository**: owner/repo`.
> 2. **BAN ON `<sub>` HTML TAGS**: Use clean markdown italics for disclaimers.
> 3. **AUTO-DEPENDENCY INSTALLATION**: Automatically checks for `requirements.txt` and installs packages into the agent virtual environment.

---

## 🛠️ Execution Command

Execute the repository cloner script:

```bash
python3 skills/utility/github-cloner/scripts/clone_repo.py <GITHUB_URL> [--type auto|plugin|skill|repo]
```

---

## 📋 Standard Confirmation Report Template

```markdown
📦 **GITHUB REPOSITORY INSTALLATION REPORT**

**Repository**: [OWNER]/[REPO]
**Destination Path**: `~/.hermes/repos/[REPO]`
**Status**: 🟢 [Cloned / Updated]
**Detected Type**: [External Tool / Plugin / Skill]
**Python Dependencies**: [Installed / None required]

---
*Hermes now has full file-system and execution access to this repository.*
```
