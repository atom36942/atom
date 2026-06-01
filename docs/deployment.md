# Deployment Guide

This guide explains how to deploy the Atom application.

## Docker Deployment

The application includes a `Dockerfile` for easy containerization.

1. **Build the image**
   ```bash
   docker build -t atom .
   ```

2. **Run the container**
   ```bash
   docker run --rm -p 8000:8000 --env-file .env atom
   ```

## Cloud Native Deployments
Atom is designed to be cloud-agnostic and can easily be deployed to AWS (ECS/EKS), Azure (Container Apps), or Google Cloud (Cloud Run).

*Details on specific cloud deployments can be added here.*
