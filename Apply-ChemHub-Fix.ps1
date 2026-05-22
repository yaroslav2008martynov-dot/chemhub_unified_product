$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'ChemHub v9 UI Fix Patch: elements + upload + admin login'
if (!(Test-Path 'patch_files')) { throw 'patch_files folder not found' }
Write-Host '[1/4] Copying frontend files...'
Copy-Item -Recurse -Force 'patch_files\apps\site\src\*' 'apps\site\src\'
Copy-Item -Recurse -Force 'patch_files\apps\agent\src\*' 'apps\agent\src\'
Copy-Item -Recurse -Force 'patch_files\apps\admin\src\*' 'apps\admin\src\'
Write-Host '[2/4] Rebuilding changed frontend services only...'
docker compose build site agent admin
Write-Host '[3/4] Starting services...'
docker compose up -d site agent admin api
Write-Host '[4/4] Done.'
Write-Host 'Open:'
Write-Host 'Site:  http://localhost:3000'
Write-Host 'Agent: http://localhost:5173'
Write-Host 'Admin: http://localhost:3100'
Write-Host 'Press Ctrl+F5 in browser.'
