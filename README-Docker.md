# 🐳 Docker Setup for SAGA

This guide explains how to run the SAGA application using Docker and docker-compose.

## 🚀 Quick Start

1. **Run the setup script:**
   ```bash
   ./scripts/docker-setup.sh
   ```

2. **Edit your `.env` file with actual values:**
   ```bash
   cp env.example .env
   # Edit .env with your OpenAI API key and other configurations
   ```

3. **Restart the application:**
   ```bash
   docker-compose restart app
   ```

## 📁 Directory Structure

The Docker setup creates and uses these volumes:

```
saga/
├── assets/              # PDF files and datasets (volume)
├── legal_chromadb/      # ChromaDB database files (volume)
├── embedding_weights/   # Model weights cache (volume)
├── src/                 # Application source code (mounted)
└── docker-compose.yml   # Docker services configuration
```

## 🛠️ Services

### Main Services
- **app**: FastAPI application (port 8000)
- **redis**: Redis cache (port 6379)
- **mongodb**: MongoDB database (port 27017)

### Development Services (dev mode only)
- **redis-commander**: Redis web UI (port 8081)
- **mongo-express**: MongoDB web UI (port 8082)

## 🔧 Commands

### Basic Operations
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart app

# Rebuild and start
docker-compose up --build -d
```

### Development Mode
```bash
# Start with development tools (Redis Commander, Mongo Express)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View all services in dev mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

### Maintenance
```bash
# View service status
docker-compose ps

# Execute commands in app container
docker-compose exec app bash

# View app logs
docker-compose logs -f app

# Clean up volumes (⚠️ This will delete all data!)
docker-compose down -v
```

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| SAGA API | http://localhost:8000 | Main application |
| API Docs | http://localhost:8000/docs | FastAPI documentation |
| Redis Commander | http://localhost:8081 | Redis web interface (dev mode) |
| Mongo Express | http://localhost:8082 | MongoDB web interface (dev mode) |

## 📝 Environment Variables

Key environment variables in `.env`:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Database paths
CHROMADB_PATH=./legal_chromadb
REDIS_URL=redis://redis:6379/0
MONGODB_URL=mongodb://admin:password@mongodb:27017/saga?authSource=admin

# Application
EMBEDDING_WEIGHTS_DIR=embedding_weights
DEBUG=True
LOG_LEVEL=INFO
```

## 🔄 Data Persistence

All important data is persisted using Docker volumes:

- **Application code**: Mounted from host for development
- **ChromaDB data**: `./legal_chromadb` directory
- **Assets**: `./assets` directory for PDFs and datasets
- **Embedding weights**: `./embedding_weights` for model caches
- **Redis data**: Docker volume `redis_data`
- **MongoDB data**: Docker volume `mongodb_data`

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: If ports 8000, 6379, or 27017 are in use:
   ```bash
   # Check what's using the port
   lsof -i :8000
   
   # Stop conflicting services or change ports in docker-compose.yml
   ```

2. **Permission issues with volumes**:
   ```bash
   # Fix permissions
   sudo chown -R $USER:$USER ./assets ./legal_chromadb ./embedding_weights
   ```

3. **Environment variables not loading**:
   ```bash
   # Restart after editing .env
   docker-compose restart app
   
   # Check if .env is being read
   docker-compose exec app env | grep OPENAI
   ```

4. **ChromaDB connection issues**:
   ```bash
   # Check if directory exists and has correct permissions
   ls -la ./legal_chromadb
   
   # Recreate if needed
   rm -rf ./legal_chromadb
   mkdir -p ./legal_chromadb
   ```

### Logs and Debugging

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs app
docker-compose logs redis
docker-compose logs mongodb

# Follow logs in real-time
docker-compose logs -f app

# Debug inside container
docker-compose exec app bash
```

## 🔄 Updates and Rebuilds

When you update the code or dependencies:

```bash
# Rebuild and restart
docker-compose up --build -d

# Or rebuild specific service
docker-compose build app
docker-compose up -d app
```

## 🧹 Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes (⚠️ deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Full cleanup
docker system prune -a
```
