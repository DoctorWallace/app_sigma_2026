# Optics ICTS Port Roadmap

This document sketches a minimal plan to port Sigma Optics (DTF) into ICTS
without changing the current DTF implementation.

## Current sigmaoptics models (DTF)
- OpticsSample: sample catalog owned by a user.
- OpticsSolicitud: request/analysis workflow with status (pendiente, aceptada, etc).
- OpticsMuestra: per-request sample entries.
- OpticsResultado: report/result files linked to a request.
- OpticsAnalisisDatos: data analysis artifacts linked to a request or technician.

## Proposed ICTS mapping
- AccessProposal (accepted + facility_confocal/optics flag) -> ICTS request entry.
- ICTS "session" model (new) -> per-request technical session, similar to VDG/IMP.
- Session samples -> based on OpticsMuestra fields (identification, description, sequence).
- Results/Report -> equivalent of OpticsResultado, with ICTS access_code in filenames.
- Analysis data -> optional, could reuse OpticsAnalisisDatos semantics for uploads.

## Endpoints/templates to reuse or adapt
- Request list and detail: reuse sigmaoptics list/detail patterns.
- Session create/edit: follow sigmaimp and sigmavdg session flows.
- Results upload/download: mirror sigmaoptics results screens and storage rules.
- Dashboard: simple summary similar to sigmaimp/imp_dashboard.

## Open decisions
- Which group names map to ICTS optics technicians.
- How to migrate existing DTF requests (if needed).
- Whether OpticsSample stays in DTF or is mirrored in ICTS.
