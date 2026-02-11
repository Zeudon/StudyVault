# StudyVault Setup and Run Instructions

## Prerequisites

1. **Node.js and npm** (for frontend)
2. **Python 3.9+** (for backend)
3. **PostgreSQL** database
4. **Qdrant** vector database (optional, for full functionality)

## Backend Setup

### 1. Navigate to backend directory
```bash
cd code/webapp/backend
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the backend directory (copy from `.env.example`):
```bash
cp .env.example .env
```

Edit `.env` and configure:
- `DATABASE_URL`: Your PostgreSQL connection string
- `SECRET_KEY`: A secure random string for JWT tokens
- `OPENAI_API_KEY`: Your OpenAI API key (for embeddings)
- `QDRANT_URL`: Qdrant server URL (default: http://localhost:6333)

### 5. Set up PostgreSQL database
```sql
CREATE DATABASE studyvault;
```

### 6. Run the backend server
```bash
python main.py
```

The backend will be available at `http://localhost:8000`

## Frontend Setup

### 1. Navigate to frontend directory
```bash
cd code/webapp/frontend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Run the development server
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Optional: Qdrant Setup

### Using Docker (recommended)
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Or install locally
Follow instructions at: https://qdrant.tech/documentation/quick-start/

## Testing the Application

1. Open your browser to `http://localhost:3000`
2. Click "Sign Up" to create a new account
3. After signing up, you'll be redirected to the Library page
4. Click "Add Content" to upload PDFs or add YouTube links
5. Your content will be indexed and stored

## Notes

- The backend must be running before starting the frontend
- Make sure PostgreSQL is running and accessible
- Qdrant is optional but required for the AI chatbot functionality
- Upload directory will be created automatically at `backend/uploads`
