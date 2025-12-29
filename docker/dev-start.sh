#!/bin/bash

# Start frontend dev server in background
cd /app/frontend && npm run dev -- --host 0.0.0.0 &

# Start backend with hot-reload
cd /app && uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
