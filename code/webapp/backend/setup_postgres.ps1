# PostgreSQL Database Setup Script for Windows
# Run this after installing PostgreSQL

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "StudyVault - PostgreSQL Setup Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if PostgreSQL is installed
Write-Host "Checking PostgreSQL installation..." -ForegroundColor Yellow
$psqlCommand = Get-Command psql -ErrorAction SilentlyContinue

if (-not $psqlCommand) {
    Write-Host "❌ PostgreSQL is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install PostgreSQL from:" -ForegroundColor Yellow
    Write-Host "https://www.postgresql.org/download/windows/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "After installation, add PostgreSQL bin folder to PATH:" -ForegroundColor Yellow
    Write-Host "Usually: C:\Program Files\PostgreSQL\<version>\bin" -ForegroundColor Cyan
    exit 1
}

Write-Host "✅ PostgreSQL found: $($psqlCommand.Source)" -ForegroundColor Green
Write-Host ""

# Get PostgreSQL superuser password
Write-Host "Enter PostgreSQL superuser (postgres) password:" -ForegroundColor Yellow
$postgresPassword = Read-Host -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($postgresPassword)
$postgresPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

Write-Host ""
Write-Host "Creating database and user..." -ForegroundColor Yellow
Write-Host ""

# Create SQL commands
$sqlCommands = @"
-- Create user
CREATE USER studyvault_user WITH PASSWORD 'studyvault_pass';

-- Create database
CREATE DATABASE studyvault OWNER studyvault_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE studyvault TO studyvault_user;
"@

# Save SQL to temp file
$tempSqlFile = [System.IO.Path]::GetTempFileName()
$sqlCommands | Out-File -FilePath $tempSqlFile -Encoding UTF8

# Execute SQL commands
$env:PGPASSWORD = $postgresPass
psql -U postgres -f $tempSqlFile

# Additional permissions for PostgreSQL 15+
$grantCommands = @"
GRANT ALL ON SCHEMA public TO studyvault_user;
GRANT CREATE ON SCHEMA public TO studyvault_user;
"@

$tempGrantFile = [System.IO.Path]::GetTempFileName()
$grantCommands | Out-File -FilePath $tempGrantFile -Encoding UTF8
psql -U postgres -d studyvault -f $tempGrantFile

# Clean up
Remove-Item $tempSqlFile -ErrorAction SilentlyContinue
Remove-Item $tempGrantFile -ErrorAction SilentlyContinue
Remove-Item Env:PGPASSWORD

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "✅ Database setup complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database Name: studyvault" -ForegroundColor White
Write-Host "Username: studyvault_user" -ForegroundColor White
Write-Host "Password: studyvault_pass" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  IMPORTANT: Change the default password 'studyvault_pass' for production!" -ForegroundColor Red
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Update backend\.env file if you used different credentials" -ForegroundColor White
Write-Host "2. Run: python test_db_connection.py" -ForegroundColor White
Write-Host "3. Start the backend server: uvicorn main:app --reload" -ForegroundColor White
Write-Host ""
