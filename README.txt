ChemHub v10.12.1

Global oxidation cleanup layer.

Install:
cd C:\chemhub_unified_product
powershell -ExecutionPolicy Bypass -File .\Apply-ChemHub-v10.12.1.ps1

After install:
docker compose restart api agent site
Open http://localhost:5173 and press Ctrl+F5.
Reload PDF; old AI-agent rows do not change automatically.
