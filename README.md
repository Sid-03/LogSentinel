# LogSentinel+

Empowering you with real-time insights, intelligent error detection, and streamlined log analytics for all your systems.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Overview
**LogSentinel+** is a full-stack log analytics platform that allows users to upload, parse, visualize, and analyze logs from various systems. It provides real-time log viewing, advanced filtering, analytics dashboards, and actionable insights for error detection and monitoring.

## Features
- Upload log files in multiple formats (JSON, CSV, custom, etc.)
- Real-time log viewer with live updates
- Interactive dashboard with log analytics (level distribution, logs per hour, etc.)
- Advanced search and filtering (by date, level, keywords, logic)
- Export logs in various formats
- Intelligent error detection and suggestions
- Upload history and parsed log browsing
- Modern, responsive UI built with React and Tailwind CSS

## Tech Stack
- **Frontend:** React, Tailwind CSS, Chart.js, React Router
- **Backend:** FastAPI, SQLAlchemy, Celery, PostgreSQL, Redis
- **Containerization:** Docker, Docker Compose
- **Other:** Nginx (serves frontend in production), Alembic (migrations)

## Architecture
```
[User]
   |
[React Frontend (Nginx)]
   |
[FastAPI Backend] -- Celery Worker
   |                   |
[PostgreSQL]       [Redis]
```
- The frontend communicates with the backend via REST APIs.
- Log uploads are parsed and stored in the database.
- Analytics and reports are generated on the backend and visualized in the frontend.
- Background tasks (e.g., heavy parsing) are handled by Celery workers.

## Getting Started
### Prerequisites
- Docker & Docker Compose (recommended)
- Node.js (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Quickstart (with Docker Compose)
```bash
git clone https://github.com/Sid-03/LogSentinel.git
cd LogSentinel
cp backend/.env.example backend/.env  # Edit as needed
docker compose up --build
```
Visit [http://localhost:3000](http://localhost:3000) for the frontend and [http://localhost:8000/docs](http://localhost:8000/docs) for the FastAPI docs.

### Local Development
- **Frontend:**
  ```bash
  cd frontend
  npm install
  npm start
  ```
- **Backend:**
  ```bash
  cd backend
  pip install -r requirements.txt
  uvicorn app.main:app --reload
  ```

## Usage
- Upload log files from the dashboard.
- View real-time and historical logs.
- Use filters and search to find relevant logs.
- Analyze trends and errors via dashboard charts.
- Export logs as needed.

## Project Structure
```
LogSentinel/
├── backend/          # FastAPI backend, log parsers, DB models, Celery tasks
│   ├── app/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # React app, Tailwind CSS, Chart.js
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](LICENSE)
