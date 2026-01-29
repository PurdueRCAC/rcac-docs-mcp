# RCAC MCP Server

Purdue RCAC MCP Server: Enables agentic development with HPC clusters and storage services.

## Installation

```bash
uv sync
```

## Usage

### Local Development (stdio)

```bash
rcac-mcp
```

### HTTP Server

```bash
rcac-mcp -t http -p 8000
```

### With JWT Authentication

```bash
export JWT_SECRET="your-secret-key-at-least-32-characters"
rcac-mcp -t http -a jwt

# Generate a token for testing
rcac-mcp --generate-token --lifetime 86400
```

## Docker Development with TLS

### Setup certificates with mkcert

```bash
# Install mkcert if needed
brew install mkcert
mkcert -install

# Generate certificates
mkdir -p certs
mkcert -cert-file certs/cert.pem -key-file certs/key.pem mcp.rcac.dev localhost 127.0.0.1

# Add to /etc/hosts
echo "127.0.0.1 mcp.rcac.dev" | sudo tee -a /etc/hosts
```

### Run with Docker Compose

```bash
docker compose up
```

The server will be available at `https://mcp.rcac.dev:8443`.

### Generate a token

```bash
export JWT_SECRET="dev-secret-at-least-32-characters-long"
rcac-mcp --generate-token
```

## Available Tools

- `nth_prime(n)` - Compute the n-th prime number (1-indexed)
- `pi_digit(n)` - Return the n-th digit of π after the decimal point

## License

MIT
