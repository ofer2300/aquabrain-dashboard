# AquaBrain V3.0 - Development Protocol

## Core Rules

### No Mocking
- **NEVER** use mock data for engineering calculations
- All hydraulic values must come from real formulas (Hazen-Williams, Darcy-Weisbach)
- Test with realistic pipe data, not placeholder values

### Design Fidelity
- UI must reflect actual calculation states
- Error states must show real engineering feedback
- All numbers displayed must be traceable to source calculations

### Glassmorphism UI
- Use `backdrop-blur-xl` for glass effects
- Semi-transparent backgrounds: `bg-slate-900/80`
- Border highlights: `border border-white/10`
- Consistent dark theme throughout

---

## Monorepo Architecture

```
aquabrain-dashboard/
├── backend/                    # Python FastAPI
│   ├── main.py                 # API endpoints
│   ├── clash_service.py        # MEP clash resolution
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── hydraulics.py       # Hazen-Williams calculator
│   │   └── standards.py        # NFPA 13 validator
│   ├── requirements.txt
│   └── venv/
│
├── frontend/                   # Next.js 15 + React 19
│   ├── src/
│   │   ├── app/                # App router pages
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom hooks
│   │   └── services/
│   │       ├── api.ts          # General API calls
│   │       └── sprinklerApi.ts # Hydraulic calculations
│   ├── package.json
│   └── tailwind.config.ts
│
├── .github/
│   └── copilot-instructions.md # Project constitution
└── CLAUDE.md                   # This file
```

---

## Backend Modules

### HydraulicCalculator (`hydraulics.py`)
```python
calculate_pressure_loss(pipe: PipeData) -> float  # PSI
calculate_velocity(flow_gpm, diameter_inch) -> float  # fps
validate_velocity(velocity_fps) -> dict
calculate(pipe: PipeData) -> HydraulicResult
```

### NFPA13Validator (`standards.py`)
```python
get_requirements(hazard_class) -> HazardRequirements
validate(hazard_class, density, spacing, coverage, pressure) -> ValidationResult
calculate_required_flow(hazard_class, area) -> float  # GPM
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/calc/hydraulic` | Hazen-Williams calculation |
| GET | `/api/status` | System status |
| POST | `/api/clash/resolve` | MEP clash resolution |
| POST | `/api/chat` | AI chat interface |
| GET | `/api/health` | Health check |

---

## Frontend Services

### sprinklerApi.ts
```typescript
calculateHydraulic(input: HydraulicInput): Promise<HydraulicOutput>
calculateMultiplePipes(segments[], hazardClass): Promise<Map<string, HydraulicOutput>>
getTotalPressureLoss(results): number
isSystemCompliant(results): boolean
```

### Unit Conversions
- `mmToInches()` / `inchesToMm()`
- `lpmToGpm()` / `gpmToLpm()`
- `barToPsi()` / `psiToBar()`
- `metersToFeet()`

---

## Development Commands

```bash
# Backend
cd backend && source venv/bin/activate && python main.py

# Frontend
cd frontend && npm run dev

# Both run on:
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Validation Protocol

1. **Input Validation** - Pydantic models with constraints
2. **Engineering Bounds** - Physical limits (positive values, max velocity)
3. **NFPA Compliance** - Hazard class requirements
4. **Warnings** - Velocity exceeds recommended (20 fps)
5. **Critical Alerts** - Velocity exceeds maximum (32 fps)
