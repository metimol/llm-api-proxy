# 🚀 LLM API Proxy

LLM API Proxy is a powerful and flexible application designed to manage HTTP requests and responses for various Large Language Model (LLM) adapters. It supports multiple adapters, including GPT, GPT4Free, HuggingChat, and more. With a built-in web frontend and MySQL database integration, it provides a seamless experience for developers. ✨

## 🎯 Purpose

This software serves as a unified interface for interacting with different LLM adapters. It allows users to send requests to various LLMs and receive responses in a consistent format. 📡

---

## 🚀 Deployment

### 📌 Prerequisites

- 🐳 Docker

### 🔧 Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/metimol/llm-api-proxy.git
   cd llm-api-proxy
   ```

2. Build and run the Docker container:

   ```bash
   docker build -t llm-api-proxy .
   docker run -d -p 3000:3000 \
     -e DB_HOST=your_db_host \
     -e DB_PORT=your_db_port \
     -e DB_USER=your_db_user \
     -e DB_PASSWORD=your_db_password \
     -e DB_NAME=your_db_name \
     -e password=your_api_key_here \
     llm-api-proxy
   ```

3. Access the application at: [`http://localhost:3000`](http://localhost:3000) 🌍

---

## ⚙️ Configuration

The configuration file is located at `./data/config.yaml`. If the file is missing, it will be automatically generated with default values. 🛠️

### 🔑 Setting the API Key

To access the API and web interface, you need to set an API key as an environment variable named `password`. If no password is set, the default password is `123456789`. 🔐

#### Set the `password` in your terminal:

```bash
export password=your_api_key_here
```

Replace `your_api_key_here` with your secret password. 🔏

#### Set the `password` in Docker:

Add the following line to the `docker run` command:

```bash
-e password=your_api_key_here
```

Replace `your_api_key_here` with your secret password. 🔄

---

## 📡 Sending Requests

You can send HTTP requests using tools like `curl` or Postman. The primary endpoint for sending requests is `/v1/chat/completions`. 📩

### 📝 Example request:

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

---

## 🌐 Web Frontend

The application comes with a web frontend located in the `web` directory. You can access it at [`http://localhost:3000`](http://localhost:3000). 🖥️

---

## 🗄️ Database Management

LLM API Proxy uses MySQL for database management. Configuration details can be found in `./data/config.yaml`. 🗃️

---

## 📜 License

This project is licensed under the MIT License. See the [`LICENSE`](LICENSE) file for more details. 📄
