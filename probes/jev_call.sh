#!/bin/sh
# Usage: probes/jev_call.sh request.json  -> Jev decision via OpenRouter
curl -s https://openrouter.ai/api/alpha/decisions -H "Authorization: Bearer $OPENROUTERS_MINE" -H "Content-Type: application/json" -d @"$1"
