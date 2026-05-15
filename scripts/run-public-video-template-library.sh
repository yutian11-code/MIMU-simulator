#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

npm run prisma:generate
npm run db:migrate
npm run build

node dist/src/scripts/run-public-video-template-library.js "$@"
