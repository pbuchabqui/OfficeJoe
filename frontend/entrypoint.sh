#!/bin/sh
echo "Starting frontend server..."
echo "Current user: $(whoami)"
echo "App directory contents:"
ls -la /app

echo ""
echo "Dist directory contents:"
ls -la /app/dist/

echo ""
echo "Starting serve on port 3000..."
exec serve -s /app/dist -l 3000
