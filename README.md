# KerfSuite 

The unified monorepo for the KerfSuite manufacturing software ecosystem by SynonTech.

## Architecture

This repository uses a monorepo structure to house all front-end clients that interact with the shared KerfSuite Supabase backend.

```
KerfSuite/
├── apps/
│   ├── kerfcut/      # The desktop application (Python/PyQt6) for CNC routing and panel saw operation.
│   ├── kerfportal/   # The web dashboard (Next.js) for admin management and CDKey generation.
│   └── kerfstock/    # The mobile application (Flutter) for workshop inventory management.
├── shared/
│   └── supabase/     # Shared database schema and migrations.
```

## Licensing

This project is governed by the SynonTech Proprietary Source License. See `LICENSE.txt` for details. Unauthorized distribution, copying, or use is strictly prohibited.
