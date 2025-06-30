# -------- Frontend Build Stage --------
FROM node:20 AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# -------- Backend Stage --------
FROM python:3.10-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy frontend build to backend static folder
COPY --from=frontend-build /app/frontend/dist ./static

EXPOSE 5000

CMD ["python", "server.py"]
