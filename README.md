# LLM API Proxy

LLM API Proxy is a versatile application designed to handle HTTP requests and responses for various Large Language Model (LLM) adapters. It supports multiple LLM adapters like GPT, GPT4Free, HuggingChat, and more. The application includes a web frontend and uses MySQL for database management.

## Purpose

The purpose of this software is to provide a unified interface for interacting with different LLM adapters. It allows users to send requests to various LLMs and receive responses in a consistent format.

## Deployment

### Prerequisites

- Docker
- Docker Compose

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/metimol/llm-api-proxy.git
   cd llm-api-proxy
   ```

2. Build and run the Docker containers:

   ```bash
   docker-compose up --build
   ```

3. The application will be available at `http://localhost:3000`.

## Usage

### Configuration

The application configuration is stored in `./data/config.yaml`. If the file does not exist, it will be created automatically with default values.

### Sending Requests

You can send HTTP requests to the application using tools like `curl` or Postman. The main endpoint for sending requests is `/v1/chat/completions`.

Example request:

```bash
curl -X POST http://localhost:3000/v1/chat/completions \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
           "model": "gpt-3.5-turbo",
           "messages": [{"role": "user", "content": "Hello, world!"}],
           "stream": false
         }'
```

### Web Frontend

The application includes a web frontend located in the `web` directory. You can access it at `http://localhost:3000`.

### Database Management

The application uses MySQL for database management. The database configuration can be found in the `./data/config.yaml` file.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
