param(
  [string]$Remote = "gdrive:nova_laptop_backup",
  [string]$Source = "."
)
Set-StrictMode -Version Latest
rclone sync $Source $Remote --exclude ".venv/**" --exclude "data/lake/tmp/**" --progress
