#!/bin/bash
export PYTHONPATH=/home/ubuntu/Rasa:$PYTHONPATH
echo "🚀 Starting Alya Image Tools Engine on port 5050..."
exec /home/ubuntu/rasa-env/bin/python3 -m addons.image_tools.server
