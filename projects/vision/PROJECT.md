# Vision: Projektkontext

GitHub-Repository `niknight1403/Vision`, Stand beim Einrichten: `dfcc2ce`.
Der README-Titel lautet derzeit AutonomAgent. Erkunde den aktuellen Code selbst,
bevor du Architektur- oder Produktannahmen triffst.

- `apps/mobile`: Expo/React Native Client.
- `services/api`: Fastify API mit Auftragswarteschlange und Freigaben.
- `services/vision-worker`: Python Vision-Analyse und Spezialisten.
- `packages/trading-core`: reine Berechnungen für Risiko und Handel.

Prüfe `npm ci`, `npm run typecheck`, `npm test` und, wenn die Python-Abhängigkeiten
verfügbar sind, die Tests unter `services/vision-worker/tests/`. Führe nur
Checks aus, deren Voraussetzungen im Lauf gegeben sind; dokumentiere Ausfälle.

Keine realen Käufe, Listings, Zahlungen oder Deployments. Fehlende Provider-
Verträge, Zugangsdaten und reale Marktbelege dürfen nicht simuliert werden.
Arbeite ohne kostenpflichtige Ressourcen. Secrets gehören ausschließlich auf
den Server; verändere weder Secrets noch Workflows oder produktive Daten.
