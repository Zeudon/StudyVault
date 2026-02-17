# PostgreSQL Setup Guide for StudyVault

## Prerequisites

Your project is already configured to use PostgreSQL. You just need to:
1. Install PostgreSQL
2. Create a database and user
3. Configure your `.env` file

## Step 1: Install PostgreSQL

### Windows

1. Download PostgreSQL from [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
2. Run the installer (recommended version: 15 or later)
3. During installation:
   - Remember the password you set for the `postgres` superuser
   - Default port: `5432` (keep this)
   - Install pgAdmin 4 (GUI tool for managing PostgreSQL)

4. Add PostgreSQL to your PATH (if not done automatically):
   - Usually located at: `C:\Program Files\PostgreSQL\<version>\bin`

### Verify Installation

Open PowerShell and run:
```powershell
psql --version
```

## Step 2: Create Database and User

### Option A: Using PowerShell (Command Line)

1. Connect to PostgreSQL as superuser:
```powershell
psql -U postgres
```

2. Enter the password you set during installation

3. Run these SQL commands:
```sql
-- Create a new user
CREATE USER studyvault_user WITH PASSWORD 'studyvault_pass';

-- Create the database
CREATE DATABASE studyvault OWNER studyvault_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE studyvault TO studyvault_user;

-- Connect to the database
\c studyvault

-- Grant schema privileges (PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO studyvault_user;
GRANT CREATE ON SCHEMA public TO studyvault_user;

-- Exit
\q
```

### Option B: Using pgAdmin 4 (GUI)

1. Open pgAdmin 4
2. Right-click on "Login/Group Roles" → Create → Login/Group Role
   - General tab: Name: `studyvault_user`
   - Definition tab: Password: `studyvault_pass`
   - Privileges tab: Check "Can login?"
3. Right-click on "Databases" → Create → Database
   - Database: `studyvault`
   - Owner: `studyvault_user`

## Step 3: Configure Environment Variables

A `.env` file has been created in the `backend` folder. Update these values:

```env
DATABASE_URL=postgresql://studyvault_user:studyvault_pass@localhost:5432/studyvault
```

**Important**: Change the default password `studyvault_pass` to something more secure!

If you used different credentials, update the format:
```
postgresql://[username]:[password]@[host]:[port]/[database_name]
```

## Step 4: Test Database Connection

Run this verification script:
```powershell
cd code\webapp\backend
python test_db_connection.py
```

## Step 5: Initialize Database Tables

The application automatically creates tables on startup. Simply run:

```powershell
# Navigate to backend directory
cd code\webapp\backend

# Activate virtual environment (if not already active)
..\..\..\.venv\Scripts\Activate.ps1

# Run the backend server
uvicorn main:app --reload
```

The tables will be created automatically when the server starts.

## Troubleshooting

### Connection Refused
- Verify PostgreSQL service is running:
  ```powershell
  Get-Service -Name postgresql*
  ```
- If not running, start it:
  ```powershell
  Start-Service postgresql-x64-15  # adjust version number
  ```

### Authentication Failed
- Double-check your credentials in the `.env` file
- Ensure the user has proper privileges

### "Database does not exist"
- Make sure you created the `studyvault` database
- Check for typos in the database name

### Port Already in Use
- Default PostgreSQL port is 5432
- Check if another database is using this port
- Update the port in `DATABASE_URL` if needed

## Verify Tables Were Created

Connect to your database:
```powershell
psql -U studyvault_user -d studyvault
```

List tables:
```sql
\dt
```

You should see:
- `users`
- `library_items`

## Security Recommendations

1. **Change default password**: Use a strong password for production
2. **Update SECRET_KEY**: Generate a secure random key for JWT tokens
3. **Never commit `.env`**: The `.env` file is in `.gitignore`
4. **Use environment-specific configs**: Different credentials for dev/prod

## Next Steps

Once PostgreSQL is set up:
1. Configure other services (Qdrant for vector storage, OpenAI API)
2. Start the backend server
3. Access your API at `http://localhost:8000/docs`
