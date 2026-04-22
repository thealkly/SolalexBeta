## Was ändert sich?

<!-- Kurze Zusammenfassung. Keine Marketing-Sprache. -->

## Story-Bezug

<!-- Verweis auf Story-Datei aus _bmad-output/implementation-artifacts/ -->

Story: `<story-key>`

## Acceptance-Criteria-Check

- [ ] Alle AC der Story sind erfüllt und durch Tests abgedeckt
- [ ] `CHANGELOG.md` aktualisiert (Root + `addon/` falls Add-on betroffen)
- [ ] `README.md` / `addon/DOCS.md` bei nutzerseitigen Änderungen aktualisiert
- [ ] Keine neuen externen Port-Expositionen (NFR28 — 100 % lokal)
- [ ] Keine CDN-Requests hinzugefügt (Fonts, JS, CSS)
- [ ] Backend: `ruff check`, `mypy --strict`, `pytest` lokal grün
- [ ] Frontend: `npm run check`, `npm run build` lokal grün

## Screenshots / Logs (falls relevant)
