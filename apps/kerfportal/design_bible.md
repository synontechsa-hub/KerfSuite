# KerfPortal — Design Bible
**Version:** 0.1.0
**Author:** SynonTech
**Status:** Draft

---

## Table of Contents

1. [Product Vision](#product-vision)
2. [Target Audience](#target-audience)
3. [The Kerf Suite Ecosystem](#the-kerf-suite-ecosystem)
4. [Core Features](#core-features)
5. [Domain Model](#domain-model)
6. [Tech Stack & Architecture](#tech-stack--architecture)
7. [Design Language](#design-language)
8. [Future Roadmap](#future-roadmap)

---

## Product Vision

KerfPortal is the **centralized command center** for the Kerf Suite of manufacturing software. 

It is a cloud-based web application where workshop owners and managers govern their digital ecosystem. Instead of managing licenses, users, and billing individually within desktop apps like KerfCut or mobile apps like KerfStock, everything is handled in one unified dashboard.

KerfPortal is the administrative hub. It does not perform optimization (KerfCut) or inventory tracking (KerfStock). It manages the *people* and *machines* that do.

---

## Target Audience

The primary user of KerfPortal is the **Workshop Owner, Manager, or IT Admin**. 

They are sitting at a desk (or on an iPad on the floor). They need high-level visibility and control. They want to know:
- Who has access to our software?
- Which machines are licensed?
- What are we paying for?
- How do I download the latest version for the new PC we just bought?

---

## The Kerf Suite Ecosystem

KerfPortal sits above the individual applications:

```text
                  ┌────────────────────────┐
                  │       KerfPortal       │
                  │   (Admin, Web-based)   │
                  └───────────┬────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ KerfCut  │        │ KerfStock│        │ KerfQuote│
    │(Desktop) │        │(Mobile/PC│        │ (Future) │
    └──────────┘        └──────────┘        └──────────┘
```

When a user opens KerfCut or KerfStock, the app talks to Supabase to verify its license and user access — all of which was defined in KerfPortal.

---

## Core Features

### 1. Unified Dashboard
A high-level view of the workshop's software footprint.
- Total active machines.
- Number of active users.
- Quick links to download the latest software installers.

### 2. License & Machine Management
The core security feature for the suite.
- **Generate CDKeys:** Create keys to activate new desktop or mobile clients.
- **Machine Binding View:** See exactly which `Machine ID` (MAC + SID + Disk Serial) is bound to which CDKey.
- **Revocation:** If a workshop PC dies or is retired, the admin can click "Revoke" to free up the license slot and instantly lock out the old machine.

### 3. User & Role Management
Control who can do what.
- Invite users via email.
- Assign roles (Admin, Member, Companion/Floor Worker).
- Assign app access (e.g., User A gets KerfStock, User B gets KerfCut and KerfStock).

### 4. Application Downloads
A secure portal to download the latest `.exe` or mobile app packages, complete with release notes.

---

## Domain Model

### Workspace (Tenant)
The top-level entity. Represents a single company/workshop.
```json
{
  "id": "ws_123",
  "name": "Oak & Iron Fabricators",
  "owner_id": "user_01"
}
```

### User
A human interacting with the system.
```json
{
  "id": "user_02",
  "workspace_id": "ws_123",
  "email": "john@oakandiron.com",
  "role": "member"
}
```

### License Slot (CDKey)
The authorization for a machine to run a specific app.
```json
{
  "id": "lic_999",
  "workspace_id": "ws_123",
  "app": "kerfcut",
  "cdkey": "KCT-PRO-A1B2-C3D4",
  "bound_machine_id": "F4B2-998A-1234-5678",
  "status": "active"
}
```

---

## Tech Stack & Architecture

- **Frontend Framework:** Next.js (React)
- **Styling:** Vanilla CSS / CSS Modules (Tailwind avoided for maximum custom styling flexibility).
- **Backend / Database:** Supabase (Postgres). Shares the same database instance as KerfCut and KerfStock.
- **Authentication:** Supabase Auth (Email/Password & Magic Links).
- **Hosting:** Vercel (recommended for Next.js) or any static hosting if exported.

---

## Design Language

KerfPortal must feel **Rugged, Industrial, and Professional**. It should look like the control panel of a high-end CNC machine, not a generic SaaS app.

- **Industrial Dark Mode:** Deep charcoal and matte black backgrounds (`#1A1A1A`, `#222222`) that resemble heavy machinery and reduce glare in the workshop.
- **High-Contrast Accents:** Use safety/industrial orange (`#E67E22` or `#F39C12`) as the primary accent color, paired with bright status colors (neon green for 'Running', red for 'Error') for instant readability from a distance.
- **Flat & Solid Panels:** Absolutely no glassmorphism or soft shadows. Use flat, solid dark-grey panels with subtle borders to compartmentalize data — like machined metal plates bolted together.
- **Utilitarian Typography:** Highly legible, geometric sans-serif fonts (like `Inter` or `Roboto`). Use uppercase styling for headers and labels to mimic industrial stencils and machine interfaces.
- **Grid-Based Density:** The layout should be strictly compartmentalized (like a dashboard of gauges and readouts). Information must be dense but distinctly separated by rigid panel borders.

---

## Future Roadmap

1. **Billing Integration:** Stripe integration for managing SaaS subscriptions (adding/removing seats).
2. **Global Activity Feed:** A unified audit log showing "John generated a KerfCut license", "Mike consumed 5 sheets in KerfStock".
3. **Cross-App Insights:** Analytics combining data from KerfCut (yield efficiency) and KerfStock (inventory value).
