<#
.SYNOPSIS
Non-destructive migration helper from local operix_db (PostgreSQL 18) to managed cloud PostgreSQL (Neon / Supabase).
Does NOT modify or reset the local database.
Usage:
  $env:LOCAL_PG_PASSWORD = "<local_postgres_password>"
  $env:PROD_DATABASE_URL = "postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require"
  .\scripts\migrate_to_prod_db.ps1
#>
$ErrorActionPreference = "Stop"

$pgBin = "C:\Program Files\PostgreSQL\18\bin"
$pgDump = Join-Path $pgBin "pg_dump.exe"
$psql = Join-Path $pgBin "psql.exe"

if (-not $env:LOCAL_PG_PASSWORD) {
    throw "Set LOCAL_PG_PASSWORD before running."
}
if (-not $env:PROD_DATABASE_URL) {
    throw "Set PROD_DATABASE_URL (libpq URI with sslmode=require) before running."
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dumpSql = Join-Path $env:TEMP "operix_db_migration_$timestamp.sql"

Write-Host "1. Exporting schema and data from local operix_db (read-only)..."
$env:PGPASSWORD = $env:LOCAL_PG_PASSWORD
& $pgDump -h localhost -p 5432 -U postgres -d operix_db --no-owner --no-privileges --clean --if-exists -f $dumpSql
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed!" }

Write-Host "2. Ensuring citext extension exists on destination PostgreSQL..."
& $psql $env:PROD_DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS citext;"
if ($LASTEXITCODE -ne 0) { throw "Failed to create citext extension on destination DB." }

Write-Host "3. Restoring schema and data to destination PostgreSQL..."
& $psql $env:PROD_DATABASE_URL -v ON_ERROR_STOP=1 -f $dumpSql
if ($LASTEXITCODE -ne 0) { throw "Restore failed!" }

Write-Host "4. Verifying table counts on destination PostgreSQL..."
& $psql $env:PROD_DATABASE_URL -c "SELECT 'factories' AS tbl, COUNT(*) FROM factories UNION ALL SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'factory_memberships', COUNT(*) FROM factory_memberships UNION ALL SELECT 'roles', COUNT(*) FROM roles UNION ALL SELECT 'permissions', COUNT(*) FROM permissions UNION ALL SELECT 'role_permissions', COUNT(*) FROM role_permissions;"

Remove-Item $dumpSql -ErrorAction SilentlyContinue
Write-Host "Migration and verification complete!"
