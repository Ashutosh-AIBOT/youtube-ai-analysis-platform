#!/bin/bash

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -f "python manage.py|uvicorn" 2>/dev/null
sleep 2

# Path to conda
CONDA_PATH=~/miniconda3/etc/profile.d/conda.sh

# Start YouTube Service (port 8005)
echo "1. Starting YouTube Service (port 8005)..."
source $CONDA_PATH
conda activate fullstack_env
cd youtube_app
uvicorn main:app --port 8005 --host 0.0.0.0 &
YOUTUBE_PID=$!
cd ..

sleep 3

# Start Sentiment Service (port 8010)
echo "2. Starting Sentiment Service (port 8010)..."
cd fastapi_services/sentiment
uvicorn main:app --port 8010 --host 0.0.0.0 &
SENTIMENT_PID=$!
cd ../..

sleep 3

# Start RAG Worker (port 8011)
echo "3. Starting RAG Worker (port 8011)..."
cd fastapi_services/rag_worker
uvicorn main:app --port 8011 --host 0.0.0.0 &
RAG_PID=$!
cd ../..

sleep 3

# Start Django (port 8000)
echo "4. Starting Django (port 8000)..."
cd django_app
python manage.py runserver 8000 &
DJANGO_PID=$!
cd ..

echo "Services started. PIDs: $YOUTUBE_PID, $SENTIMENT_PID, $RAG_PID, $DJANGO_PID"
echo "Access Django at http://localhost:8000"

# Keep script running to monitor or wait
wait
