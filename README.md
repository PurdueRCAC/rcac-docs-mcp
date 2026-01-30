# RCAC MCP Server

Purdue RCAC MCP Server: Enables agentic development with HPC clusters and storage services.

## Quick Start (Desktop Clients)

For MCP-enabled desktop applications like Raycast, Claude Desktop, or Cursor, add this server
to your MCP configuration:

```json
{
  "mcpServers": {
    "rcac": {
      "command": "uvx",
      "args": ["git+https://github.com/purduercac/rcac-mcp"]
    }
  }
}
```

This runs the server locally in `stdio` mode — no additional setup required.

## Hosted HTTP Server

For a shared hosted instance with authentication:

### Basic HTTP Server

```bash
rcac-mcp -t http -p 8000
```

### With JWT Authentication

```bash
export JWT_SECRET="your-secret-key-at-least-32-characters"
rcac-mcp -t http -a jwt

# Generate a token for clients
rcac-mcp --generate-token --lifetime 86400
```

### Docker Compose with TLS

For production-like deployments with HTTPS:

```bash
# Install mkcert if needed
brew install mkcert
mkcert -install

# Generate certificates
mkdir -p certs
mkcert -cert-file certs/cert.pem -key-file certs/key.pem mcp.rcac.dev localhost 127.0.0.1

# Add to /etc/hosts
echo "127.0.0.1 mcp.rcac.dev" | sudo tee -a /etc/hosts

# Run
docker compose up
```

The server will be available at `https://mcp.rcac.dev:8443`.

## Development

```bash
uv sync
rcac-mcp
```

## Available Tools

- `nth_prime(n)` - Compute the n-th prime number (1-indexed)
- `pi_digit(n)` - Return the n-th digit of π after the decimal point

## License

MIT
