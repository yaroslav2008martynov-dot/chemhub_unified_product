$ErrorActionPreference = 'Stop'
Write-Host 'ChemHub v9.3.1 safe hotfix: smoke-test + duplicate cleanup'

if (!(Test-Path '.\docker-compose.yml')) {
  Write-Host 'ERROR: run this script from C:\chemhub_unified_product'
  exit 1
}

$backup = "backup_before_v9_3_1_$(Get-Date -Format yyyyMMdd_HHmmss)"
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item .\apps\api\app\extractor.py "$backup\extractor.py" -ErrorAction SilentlyContinue
Copy-Item .\apps\api\app\processor.py "$backup\processor.py" -ErrorAction SilentlyContinue
Copy-Item .\apps\site\src\main.jsx "$backup\site_main.jsx" -ErrorAction SilentlyContinue
Copy-Item .\apps\site\src\styles.css "$backup\site_styles.css" -ErrorAction SilentlyContinue
Write-Host "Backup created: $backup"

Write-Host 'Applying DB compatibility defaults...'
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;"
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS hidden BOOLEAN DEFAULT FALSE;"
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT TRUE;"
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS impossible_note TEXT;"
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;"

Write-Host 'Updating simple canonical keys without risky regex...'
docker compose exec -T postgres psql -U chemhub -d chemhub -c "UPDATE reactions SET canonical_equation = lower(replace(replace(replace(coalesce(equation,''),' ',''),'→','='),'⇌','=')) WHERE canonical_equation IS NULL OR canonical_equation = '';"
docker compose exec -T postgres psql -U chemhub -d chemhub -c "UPDATE job_reactions SET canonical_equation = lower(replace(replace(replace(coalesce(equation,''),' ',''),'→','='),'⇌','=')) WHERE canonical_equation IS NULL OR canonical_equation = '';"

Write-Host 'Hiding duplicate reactions; keeping most informative version...'
$dupSql = @"
WITH ranked AS (
  SELECT id,
         ROW_NUMBER() OVER (
           PARTITION BY canonical_equation
           ORDER BY
             (length(coalesce(conditions,'')) + length(coalesce(catalysts,'')) + length(coalesce(solvents,'')) + length(coalesce(temperature,'')) + length(coalesce(pressure,'')) + length(coalesce(reaction_name,''))) DESC,
             id ASC
         ) AS rn
  FROM reactions
  WHERE coalesce(canonical_equation,'') <> ''
)
UPDATE reactions r
SET hidden = TRUE,
    approved = FALSE,
    impossible_note = trim(coalesce(r.impossible_note,'') || ' duplicate_hidden')
FROM ranked
WHERE r.id = ranked.id AND ranked.rn > 1;
"@
$dupSql | docker compose exec -T postgres psql -U chemhub -d chemhub

Write-Host 'Restarting API and site...'
docker compose restart api site
Start-Sleep -Seconds 4

Write-Host 'Smoke test extractor inside API container...'
$smoke = "from app.extractor import extract_reactions_from_text, canonical_equation; print('IMPORT_OK'); print(canonical_equation('H2 + S -> H2S')); rs=extract_reactions_from_text('H2^0 + S -> H2+1S'); print([(r.equation, r.temperature, r.conditions) for r in rs])"
docker compose exec -T api sh -lc "cd /app && python -c \"$smoke\""

Write-Host 'Patch v9.3.1 hotfix finished.'
Write-Host 'Open site and AI Agent, then press Ctrl+F5:'
Write-Host 'Site: http://localhost:3000'
Write-Host 'AI Agent: http://localhost:5173'
