$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.3 admin bulk delete by PDF safe patch"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = "backup_before_v10_3_$ts"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

Copy-Item ".\apps\api\app\main.py" "$backup\main.py" -Force
Copy-Item ".\apps\admin\src\main.jsx" "$backup\admin_main.jsx" -Force

Copy-Item ".\patch_files\apps\admin\src\main.jsx" ".\apps\admin\src\main.jsx" -Force
python ".\patch_files\apps\api\app\patch_main_for_pdf_delete.py"

Write-Host "Checking Python syntax..."
python -m py_compile ".\apps\api\app\main.py"

Write-Host "Copying files into running containers..."
docker cp ".\apps\api\app\main.py" chemhub_unified_product-api-1:/app/app/main.py
docker cp ".\apps\admin\src\main.jsx" chemhub_unified_product-admin-1:/app/src/main.jsx

Write-Host "Restarting API and admin..."
docker compose restart api admin

Write-Host "Patch v10.3 installed."
Write-Host "Open admin and press Ctrl+F5: http://localhost:3100"
