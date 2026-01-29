FROM python:3.14-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install dependencies
RUN uv pip install --system -e .

# Default command
ENTRYPOINT ["rcac-mcp"]
CMD ["-t", "http", "-H", "0.0.0.0", "-p", "8000"]
