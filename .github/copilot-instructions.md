# AquaBrain V3.0 - Project Constitution

## Philosophy
**Trust but Verify** - All AI-generated calculations must be validated against engineering standards before deployment.

## Standard
**LOD 500** - Level of Development 500 (As-Built). All models and calculations must meet the highest level of detail and accuracy for construction documentation.

## Design
**Glassmorphism** - Modern glass-like UI with:
- Frosted glass backgrounds (`backdrop-blur-xl`)
- Subtle transparency (`bg-white/10`, `bg-black/20`)
- Soft borders (`border border-white/20`)
- Gradient accents for depth
- Dark theme optimized

---

## Engineering Principles

### Hydraulic Calculations
- All pipe sizing follows Hazen-Williams formula: `P = 4.52 * Q^1.85 / (C^1.85 * d^4.87)`
- Pressure loss calculations include fittings (K-factors)
- Velocity limits enforced per NFPA 13 (max 32 fps)

### Code Compliance
- Primary: NFPA 13 (Sprinkler Systems)
- Secondary: NFPA 25 (Inspection & Maintenance)
- Local: Israeli Standard SI 1596

### Quality Gates
1. No calculation without validation
2. No deployment without code compliance check
3. No mocking in production calculations

---

## Monorepo Structure

```
aquabrain-dashboard/
├── backend/           # FastAPI Python server
│   ├── main.py
│   ├── modules/
│   │   ├── hydraulics.py
│   │   └── standards.py
│   └── requirements.txt
├── frontend/          # Next.js React app
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── services/
│   │       ├── api.ts
│   │       └── sprinklerApi.ts
│   └── package.json
├── .github/
│   └── copilot-instructions.md
└── CLAUDE.md
```
