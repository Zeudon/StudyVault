# Docker Quick Reference

## Start Application
```powershell
cd code
docker-compose up --build
```

## Background Mode
```powershell
docker-compose up -d
```

## Stop Application
```powershell
docker-compose stop
```

## View Logs
```powershell
docker-compose logs -f
```

## Access Points
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs  
- Qdrant: http://localhost:6333/dashboard

## Common Commands
```powershell
# Check status
docker-compose ps

# Restart service
docker-compose restart backend

# Rebuild after changes
docker-compose up --build backend

# Remove everything
docker-compose down

# Remove with data (⚠️ DELETES DATA!)
docker-compose down -v

# Access container shell
docker exec -it rag-backend /bin/bash
```

## Service Names (for inter-container communication)
- `db` - PostgreSQL on port 5432
- `qdrant` - Qdrant on port 6333
- `backend` - FastAPI on port 8000
- `frontend` - Nginx on port 80

## Data Persistence
- PostgreSQL: `pgdata` volume
- Qdrant: `qdrant_data` volume
- Uploads: `./webapp/backend/uploads` (local bind mount)
