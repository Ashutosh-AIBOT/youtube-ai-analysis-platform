#!/bin/bash

echo "========================================="
echo "     STARTING ALL SERVICES"
echo "========================================="
echo ""

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -f "python manage.py|uvicorn" 2>/dev/null
sleep 2

# Start Django (uses rag env)
echo "1. Starting Django (port 8000)..."
gnome-terminal --title="Django (rag)" -- bash -c "
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate rag
    cd ~/Desktop/Mega-Projects/fullstack_complete/fullstack/django_app
    python manage.py runserver 8000
" 2>/dev/null &

sleep 3

# Start YouTube Service (uses youtube-ai env)
echo "2. Starting YouTube Service (port 8005)..."
gnome-terminal --title="YouTube (youtube-ai)" -- bash -c "
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate youtube-ai
    cd ~/Desktop/Mega-Projects/fullstack_complete/fullstack/youtube_app
    uvicorn main:app --reload --port 8005 --host 0.0.0.0
" 2>/dev/null &

sleep 3

# Start Sentiment Service (uses rag env)
echo "3. Starting Sentiment Service (port 8010)..."
gnome-terminal --title="Sentiment (rag)" -- bash -c "
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate rag
    cd ~/Desktop/Mega-Projects/fullstack_complete/fullstack/fastapi_services/sentiment
    uvicorn main:app --reload --port 8010 --host 0.0.0.0
" 2>/dev/null &

sleep 3

# Start RAG Worker (uses rag env)
echo "4. Starting RAG Worker (port 8011)..."
gnome-terminal --title="RAG (rag)" -- bash -c "
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate rag
    cd ~/Desktop/Mega-Projects/fullstack_complete/fullstack/fastapi_services/rag_worker
    uvicorn main:app --reload --port 8011 --host 0.0.0.0
" 2>/dev/null &

echo ""
echo "========================================="
echo "     ALL SERVICES STARTED"
echo "========================================="
echo ""
echo "Access URLs:"
echo "  Django:     http://localhost:8000"
echo "  YouTube:    http://localhost:8005/health"
echo "  Sentiment:  http://localhost:8010/health"
echo "  RAG:        http://localhost:8011/health"
echo ""
echo "4 terminals opened - one for each service"
