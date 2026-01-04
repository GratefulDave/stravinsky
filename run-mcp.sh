#!/bin/bash
cd /Users/davidandrews/PycharmProjects/stravinsky
exec /Users/davidandrews/PycharmProjects/stravinsky/.venv/bin/python -m mcp_bridge.server "$@"
