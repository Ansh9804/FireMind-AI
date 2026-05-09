Write-Host "🚀 Setting up FireMind AI project structure..."

# Create folders
New-Item -ItemType Directory -Force -Path data
New-Item -ItemType Directory -Force -Path backend
New-Item -ItemType Directory -Force -Path web

# Backend files
New-Item backend/__init__.py -ItemType File -Force
New-Item backend/server.py -ItemType File -Force
New-Item backend/embeddings.py -ItemType File -Force
New-Item backend/retrieval.py -ItemType File -Force
New-Item backend/config.py -ItemType File -Force
New-Item backend/utils.py -ItemType File -Force

# Data files
New-Item data/ferl_knowledge.json -ItemType File -Force
New-Item data/source_documents.json -ItemType File -Force
New-Item data/client_faq_answers.json -ItemType File -Force

# Web files
New-Item web/app.js -ItemType File -Force
New-Item web/index.html -ItemType File -Force
New-Item web/style.css -ItemType File -Force

# Root files
New-Item .env -ItemType File -Force
New-Item requirements.txt -ItemType File -Force
New-Item README.md -ItemType File -Force

Write-Host "✅ Project structure created successfully!"