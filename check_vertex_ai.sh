#!/bin/bash

echo "Checking Vertex AI API status..."
echo "================================"

# Check if Vertex AI API is enabled
echo -e "\n1. Checking if Vertex AI API is enabled..."
gcloud services list --enabled --project=researcharticlepodcast | grep aiplatform

# Try to enable it if not enabled
echo -e "\n2. Attempting to enable Vertex AI API..."
gcloud services enable aiplatform.googleapis.com --project=researcharticlepodcast

# Check organization policies for allowed locations
echo -e "\n3. Checking allowed regions..."
gcloud resource-manager org-policies describe constraints/gcp.resourceLocations \
    --project=researcharticlepodcast 2>/dev/null || echo "No location constraints found"

# List available regions for Vertex AI
echo -e "\n4. Common Vertex AI regions:"
echo "  - us-central1"
echo "  - us-east4"
echo "  - us-west1"
echo "  - us-west4"
echo "  - europe-west1"
echo "  - europe-west4"
echo "  - asia-southeast1"

echo -e "\n5. Try testing with this command:"
echo "gcloud ai models list --region=us-central1 --project=researcharticlepodcast"
