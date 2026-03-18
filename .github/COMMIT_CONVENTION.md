# Commit-Konventionen

Der Auto-Release Workflow kategorisiert Commits anhand des Präfixes:

| Präfix | Kategorie im Release | Beispiel |
|---|---|---|
| `feat:` / `add:` / `new:` | ✨ Neue Features | `feat: Spatial Upscaler Node hinzugefügt` |
| `fix:` / `bug:` / `patch:` | 🐛 Bugfixes | `fix: download_model.sh Pfad korrigiert` |
| `refactor:` / `update:` / `improve:` | 🔧 Änderungen | `update: ComfyUI auf v0.17.2` |
| `chore:` | 🔧 Änderungen | `chore: .gitignore aufgeräumt` |
| Alles andere | 📦 Sonstiges | `docs: README aktualisiert` |

## Version Bump Regeln

- **patch** (v1.0.0 → v1.0.1) – Bugfixes, kleine Korrekturen
- **minor** (v1.0.0 → v1.1.0) – Neue Features, neue Nodes
- **major** (v1.0.0 → v2.0.0) – Breaking Changes, neue Modellversion

## Manuelles Release auslösen

GitHub → Actions → "Auto Release" → "Run workflow" →
Bump-Typ wählen + optionale Beschreibung eintragen → Run
