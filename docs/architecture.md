# INSPECTRA — System Architecture

## Overview

INSPECTRA is a modular, AI-augmented inspection management system for Legal Metrology enforcement.
It is designed for the Ministry of Consumer Affairs to inspect packaged commodities under LM(PC) Rules, 2011.

## Module Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                             │
│   Login → Dashboard → Inspections (List/New/Detail) → Products      │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ REST API (JWT)
┌─────────────────────────▼───────────────────────────────────────────┐
│                       BACKEND (FastAPI)                             │
│                                                                     │
│  ┌────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Auth API  │  │  Products   │  │Inspections│  │  Dashboard   │  │
│  └────────────┘  └─────────────┘  └──────────┘  └──────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               Services Layer                                 │   │
│  │  InspectionService  │  StorageService  │  EvidenceService    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │            AI Agents (Phase 2 — NOT YET IMPLEMENTED)         │  │
│  │  LabelAgent  │  QuantityAgent  │  DeclarationAgent           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │            Rule Engines (Phase 2 — NOT YET IMPLEMENTED)      │  │
│  │  DeclarationEngine  │  MeasurementEngine  │  RuleLoader      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ SQLAlchemy ORM
┌─────────────────────────▼───────────────────────────────────────────┐
│                    PostgreSQL (Docker)                               │
│  users │ products │ inspections │ inspection_images                 │
│  ai_results │ compliance_checks │ evidences │ human_reviews         │
└─────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                  Storage Service                                     │
│  LocalStorageService (dev)  │  S3StorageService (production stub)   │
└─────────────────────────────────────────────────────────────────────┘
```

## Inspection Workflow

```
Inspector → Create Inspection (INS-2026-XXXXX)
         → Upload Package Images (FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM)
         → [Phase 2] AI Agents analyze images
         → [Phase 2] Rule Engine evaluates compliance
         → [Phase 2] Human Review for borderline cases
         → Inspection Closed / Report Generated
```

## Legal References

- **Legal Metrology (Packaged Commodities) Rules, 2011**
- **Rule 6** — Mandatory declarations on every package
- **Rule 18** — MRP declaration requirements
- **Schedule II** — Net quantity tolerances
