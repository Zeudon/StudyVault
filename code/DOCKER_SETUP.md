# Running StudyVault with Docker

This guide explains how to run the entire StudyVault application using Docker containers.

## Prerequisites

- **Docker Desktop** installed and running
- **Docker Compose** installed (included with Docker Desktop)
- At least 4GB of RAM allocated to Docker

## Architecture

The application consists of 4 containers:
1. **PostgreSQL** (`rag-db`) - Database on port 5432
2. **Qdrant** (`rag-qdrant`) - Vector database on ports 6333, 6334
3. **Backend** (`rag-backend`) - FastAPI on port 8000
4. **Frontend** (`rag-frontend`) - React with Nginx on port 3000

## Setup Instructions

### 1. Navigate to the code directory

```powershell
cd "C:\Nived\Nived Personal\Academia\StudyVault\code"
```

### 2. Environment Configuration

The application uses `.env.docker` for Docker deployments with proper service names:
- Database: `db` (Docker service name instead of localhost)
- Qdrant: `qdrant` (Docker service name instead of localhost)

The file is already configured at: `code/webapp/backend/.env.docker`

### 3. Build and Start All Containers

```powershell
docker-compose up --build
```

This will:
- Build all Docker images
- Create containers
- Set up networking
- Initialize databases
- Start all services

**First run may take 5-10 minutes** to build everything.

### 4. Wait for Services to Start

Watch the logs for these messages:
- `rag-db` - `database system is ready to accept connections`
- `rag-qdrant` - `Qdrant gRPC listening on`
- `rag-backend` - `Application startup complete`
- `rag-frontend` - nginx startup messages

### 5. Access the Application

Once all services are running:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Container Management

### Run in Detached Mode (Background)

```powershell
docker-compose up -d
```

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
docker-compose logs -f qdrant
```

### Stop Containers

```powershell
docker-compose stop
```

### Stop and Remove Containers

```powershell
docker-compose down
```

### Stop and Remove Everything (Including Volumes - THIS DELETES DATA!)

```powershell
docker-compose down -v
```

### Restart a Specific Service

```powershell
docker-compose restart backend
```

### Rebuild After Code Changes

```powershell
# Rebuild specific service
docker-compose up --build backend

# Rebuild everything
docker-compose up --build
```

## Data Persistence

Data is persisted using Docker volumes:

### PostgreSQL Data
- **Volume**: `pgdata`
- **Location**: Managed by Docker
- **Contents**: All user accounts, library items, and metadata

### Qdrant Data
- **Volume**: `qdrant_data`
- **Location**: Managed by Docker
- **Contents**: Vector embeddings for RAG

### Uploaded Files
- **Volume**: `./webapp/backend/uploads` (bind mount)
- **Location**: Your local filesystem
- **Contents**: PDF files uploaded by users

**Important**: Running `docker-compose down -v` will delete all database data!

## Troubleshooting

### Port Already in Use

If you see errors like "port is already allocated":

1. **Stop local services**:
   ```powershell
   # Stop local PostgreSQL
   Stop-Service postgresql-x64-*
   
   # Kill processes on specific ports
   netstat -ano | findstr :3000
   netstat -ano | findstr :8000
   netstat -ano | findstr :5432
   ```

2. **Or change ports** in `docker-compose.yml`:
   ```yaml
   ports:
     - "3001:80"  # Frontend on 3001 instead of 3000
   ```

### Database Connection Issues

If backend can't connect to database:

1. Check database is healthy:
   ```powershell
   docker-compose ps
   ```

2. Check if database name matches:
   ```powershell
   docker exec -it rag-db psql -U postgres -c "\l"
   ```

3. Verify `.env.docker` has correct settings:
   ```
   DATABASE_URL=postgresql://postgres:postgres@db:5432/studyvault
   ```

### Container Won't Start

1. **View logs**:
   ```powershell
   docker-compose logs <service-name>
   ```

2. **Check if image built correctly**:
   ```powershell
   docker images | grep rag
   ```

3. **Remove and rebuild**:
   ```powershell
   docker-compose down
   docker-compose up --build --force-recreate
   ```

### Backend Errors

1. **Access backend container**:
   ```powershell
   docker exec -it rag-backend /bin/bash
   ```

2. **Check environment variables**:
   ```bash
   env | grep DATABASE
   ```

3. **Test database connection manually**:
   ```bash
   python test_db_connection.py
   ```

### Frontend Not Loading

1. **Check nginx configuration**:
   ```powershell
   docker exec -it rag-frontend cat /etc/nginx/conf.d/default.conf
   ```

2. **Check build output**:
   ```powershell
   docker exec -it rag-frontend ls /usr/share/nginx/html
   ```

3. **View nginx logs**:
   ```powershell
   docker-compose logs frontend
   ```

## Development Workflow

### Making Backend Changes

1. Edit code in `code/webapp/backend/`
2. Rebuild backend:
   ```powershell
   docker-compose up --build backend
   ```

### Making Frontend Changes

1. Edit code in `code/webapp/frontend/`
2. Rebuild frontend:
   ```powershell
   docker-compose up --build frontend
   ```

### Database Schema Changes

1. Edit `models.py`
2. Rebuild backend (migrations will run automatically)
3. Or drop database and recreate:
   ```powershell
   docker-compose down -v
   docker-compose up --build
   ```

## Health Checks

All services have health checks:

```powershell
# Check service health status
docker-compose ps

# Should show "healthy" for all services
```

Health checks ensure:
- PostgreSQL accepts connections
- Qdrant API responds
- Backend API is accessible
- Services start in correct order

## Network Configuration

All containers are on the same Docker network (`app-network`) and can communicate using service names:

- Backend → Database: `db:5432`
- Backend → Qdrant: `qdrant:6333`
- Frontend → Backend: `backend:8000` (via nginx proxy)

## Useful Commands

```powershell
# Check running containers
docker ps

# Check all containers (including stopped)
docker ps -a

# Check Docker volumes
docker volume ls

# Inspect a volume
docker volume inspect code_pgdata

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a

# View resource usage
docker stats
```

## Production Deployment

For production deployment:

1. **Update environment variables**:
   - Change `SECRET_KEY` to a secure random value
   - Update database password
   - Configure actual domain names

2. **Enable HTTPS**:
   - Add SSL certificates to nginx
   - Update nginx.conf for HTTPS

3. **Configure OpenAI API**:
   - Add `OPENAI_API_KEY` to `.env.docker`

4. **Set up backups**:
   - Backup PostgreSQL data regularly
   - Backup Qdrant vectors
   - Backup uploaded files

5. **Use Docker secrets** for sensitive data

## Switching Between Local and Docker

### To run locally (without Docker):

1. Stop Docker containers:
   ```powershell
   docker-compose down
   ```

2. Start local PostgreSQL:
   ```powershell
   Start-Service postgresql-x64-*
   ```

3. Use `.env` (not `.env.docker`) with localhost addresses

4. Run backend and frontend as usual

### To switch back to Docker:

1. Stop local services
2. Run: `docker-compose up`

## Next Steps

After everything is running:
1. ✅ Sign up at http://localhost:3000
2. ✅ Upload PDFs or YouTube links
3. ✅ View/download your content
4. ✅ Use the chat feature (when RAG is implemented)

All your data persists in Docker volumes even after stopping containers!
