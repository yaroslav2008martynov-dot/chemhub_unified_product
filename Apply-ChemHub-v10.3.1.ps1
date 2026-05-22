$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.3.1 bulk delete route fix"

$root = Get-Location
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v10_3_1_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

Copy-Item ".\apps\api\app\main.py" "$backup\main.py" -Force
Copy-Item ".\apps\admin\src\main.jsx" "$backup\admin_main.jsx" -Force

Write-Host "Backup created: $backup"

python ".\patch_files\v10_3_1_patch.py"

Write-Host "Checking Python syntax..."
python -m py_compile ".\apps\api\app\main.py"

Write-Host "Copying into containers..."
docker cp ".\apps\api\app\main.py" chemhub_unified_product-api-1:/app/app/main.py
docker cp ".\apps\admin\src\main.jsx" chemhub_unified_product-admin-1:/app/src/main.jsx

Write-Host "Restarting API and admin..."
docker compose restart api admin

Write-Host "Patch v10.3.1 installed."
Write-Host "Open admin and press Ctrl+F5: http://localhost:3100"
