# Alternative Nyheter - News Aggregator

A modern news aggregation platform that collects and displays articles from various Norwegian and international news sources.

## Features

- 📰 Real-time news aggregation from multiple sources
- 🔍 Advanced filtering by category, source, and language
- 📱 Mobile-responsive design with dark/light mode
- ⚡ Fast API with rate limiting and caching
- 🔒 Security-first approach with CORS and input validation
- 🚀 Production-ready with Docker containers

## Architecture

- **Frontend**: Vanilla JavaScript with Tailwind CSS
- **Backend**: FastAPI with PostgreSQL database
- **Caching**: Redis for performance optimization
- **Deployment**: Docker containers with nginx proxy

## Quick Start

### Local Development

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Run with Docker:
   ```bash
   docker compose up --build
   ```
4. Access at http://localhost:3000

### Manual Refresh
```bash
curl -X POST http://localhost:8000/api/refresh
```

### Cloud Deployment Options

#### Railway
1. Fork this repository
2. Connect to Railway
3. Add environment variables
4. Deploy automatically

#### Render  
1. Fork this repository
2. Connect to Render
3. Use `render.yaml` configuration
4. Add database service

#### Fly.io
```bash
flyctl launch
flyctl deploy
```

## Configuration

Environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string  
- `ALLOWED_ORIGINS`: CORS allowed origins
- `FETCH_INTERVAL_MIN`: Minutes between news fetches

## API Endpoints

- `GET /api/articles` - List articles with filtering
- `GET /api/categories` - Available categories
- `GET /api/sources` - Available news sources
- `POST /api/refresh` - Manually trigger news fetch
- `GET /health` - Health check

## Security Features

- Rate limiting on all endpoints
- CORS protection
- Input validation and sanitization
- Structured logging
- Health checks and monitoring

## License

MIT License
