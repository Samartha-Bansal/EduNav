Set-Location "$PSScriptRoot\..\frontend"
# Cloud-synced folders (e.g. OneDrive) need polling or chunk loads can time out.
$env:WATCHPACK_POLLING = "true"
npm run dev
