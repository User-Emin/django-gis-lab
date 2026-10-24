# Bronnen les 22 — alles (gezien 24-10-2026)

| Wat | Bron |
|---|---|
| `accoreconsole /i`, `/s`, `/l en-US`; FILEDIA/CMDDIA 0 | https://static.au-uw2-prd.autodesk.com/Class_Handout_BES227196_AutoCAD_Scripting_from_the_Core_AutoCAD_Core_Console_Mike_Best.pdf (via feiten-rvb-autocad B; PDF niet opnieuw gelezen) |
| SECURELOAD 0, NETLOAD abs. pad, QSAVE, QUIT Y; paden absoluut | https://raw.githubusercontent.com/autodesk-platform-services/aps-lisp-dotnet-skill/main/skill/SKILL.md r146-164; https://raw.githubusercontent.com/autodesk-platform-services/aps-lisp-dotnet-skill/main/dotnet-outputs/FlangeDA/Tests/Integration/RunIntegrationTests.ps1 r45-58 |
| Exitcode accoreconsole | ⚠️ betekenis van de codes niet gedocumenteerd gevonden; de sample leest alleen $LASTEXITCODE |
| Geen vla-/COM, AcMgd crasht, AutoCAD.NET.Core | https://raw.githubusercontent.com/autodesk-platform-services/aps-lisp-dotnet-skill/main/SPEC.md r5; https://raw.githubusercontent.com/autodesk-platform-services/aps-lisp-dotnet-skill/main/CLAUDE.md r74; SKILL.md r14, r125 |
| Token `POST /authentication/v2/token`, Basic auth, `grant_type=client_credentials`, scopes `code:all data:read data:write bucket:create bucket:read bucket:update` | https://raw.githubusercontent.com/autodesk-platform-services/aps-lisp-dotnet-skill/main/dotnet-outputs/FlangeDA/da/APS-Common.ps1 r9, r30-41; .../da/web-demo/src/aps-client.js r10-35 |
| DA-basis `https://developer.api.autodesk.com/da/us-east/v3` | APS-Common.ps1 r7; https://raw.githubusercontent.com/Autodesk-Forge/forge-api-dotnet-design.automation/main/src/Autodesk.Forge.DesignAutomation/Configuration.gen.cs. ⚠️ andere regio's niet geverifieerd |
| `GET /forgeapps/me` (kale string) | APS-Common.ps1 r44-86; SKILL.md r135 |
| `POST /appbundles` {id, engine, description}, 409 -> `/appbundles/{id}/versions`; upload naar `uploadParameters.endpointURL` met `formData` + `file` | APS-Common.ps1 r122-165 |
| `POST /appbundles/{id}/aliases`, `/activities/{id}/aliases` {id, version} | APS-Common.ps1 r169-224; https://raw.githubusercontent.com/autodesk-platform-services/aps-design-automation-dotnet/master/designAutomationSample/Controllers/DesignAutomationController.cs r140-160, r245 |
| Activity: engine, commandLine met `/al "$(appbundles[X].path)"`, appbundles-lijst, parameters (verb, localName, required, description), settings.script.value | https://raw.githubusercontent.com/autodesk-platform-services/aps-lisp-dotnet-skill/main/dotnet-outputs/FlangeDA/da/activity.json; Deploy-And-Test-DA.ps1 r57; DesignAutomationController.cs r196, r225-240 |
| Engine `Autodesk.AutoCAD+25_0` (AutoCAD 2025) | SKILL.md tabel r44-53 (via feiten) |
| `POST /workitems` {activityId `nick.Act+alias`, arguments{naam:{url, verb, headers}}} | DesignAutomationController.cs r318, r343-385; Deploy-And-Test-DA.ps1 r70-79 |
| `GET /workitems/{id}`, status, reportUrl, stats; polling 5 s / 300 s | APS-Common.ps1 r292-330; aps-client.js r105-112 |
| Statussen pending, inprogress, cancelled, failedLimitDataSize, failedLimitProcessingTime, failedDownload, failedInstructions, failedUpload, failedUploadOptional, success | https://raw.githubusercontent.com/Autodesk-Forge/forge-api-dotnet-design.automation/main/src/Autodesk.Forge.DesignAutomation/Model/Status.gen.cs |
| 429 / Retry-After / rate limits DA | ⚠️ niet gevonden; backoff is algemene HTTP-praktijk |
| onComplete-callback | ⚠️ niet geverifieerd |
| DA-prijs | ⚠️ onbevestigd (feiten-rvb-autocad B) |
| Celery `shared_task`, `delay_on_commit` | https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html (via feiten-tech §6) |
| Officiële APS-API-referentie (aps.autodesk.com) | ⚠️ niet geopend: JS-pagina's, alleen GitHub-bronnen gebruikt |
