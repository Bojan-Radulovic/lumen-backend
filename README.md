# Lumen Backend

## Overview

The **Lumen system** is a self-hosted platform designed to offer AI agent functionalities using fully open-source tools and locally deployed models. Inspired by modern advancements in generative AI and large language models (LLMs), Lumen provides users with a secure and private alternative to popular cloud-based AI services. With a focus on data sovereignty, Lumen allows users to interact with AI-powered agents capable of performing tasks such as natural language processing (via speech-to-text and text-to-speech), email communication, image generation, web searching, and executing Python-based computations all within their own infrastructure.

## Backend Functionality

The Lumen backend is the central processing layer of the system. It manages communication between AI agents and various services using **FastStream** and **RabbitMQ**, handles local LLM execution and ensures integration with supporting modules such as TTS, image generation, and web search tools. The backend is modular and scalable, supporting multiple services running in parallel. Key features include:

- Local inference of large language models using GGUF-formatted quantized models.
- Support for CUDA acceleration for efficient model execution.
- Seamless task orchestration through message queues.
- Integration with Docker-managed services like SearXNG for private web searching.
- Image generation using Stable Diffusion models.
- Text-to-speech capabilities using locally hosted voice synthesis tools.

## System Requirements

To run the Lumen backend, the following hardware and software components were used:

**Hardware:**
- CPU: Intel Core i5-12400F  
- GPU: NVIDIA GeForce RTX 4070 SUPER (12 GB VRAM)  
- RAM: 64 GB DDR4 @ 3200 MHz  
- Motherboard: Gigabyte H610M H V3 DDR4  

**Software:**
- OS: Windows 11  
- Python: 3.9.13  
- CUDA Toolkit: 12.6 (V12.6.85)  
- RabbitMQ: 4.0  
- Docker: 28.0.1  
- MSBuild Tools: Latest (Desktop C++ only)

## Getting Started

Follow the steps below to set up and run the Lumen backend:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Bojan-Radulovic/lumen-backend.git
   cd lumen-backend
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install MSBuild Tools (Desktop C++ only):**  
   Download from: [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/?q=build+tools). Only the default installation for C++ desktop development is required.

4. **Set environment variables for CUDA build:**
   ```powershell
   $env:CMAKE_ARGS="-DGGML_CUDA=on"
   $env:FORCE_CMAKE="1"
   ```

5. **Install dependencies:**
   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

6. **Install PyTorch:**

   The following version was used in development:
   ```bash
   pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
   ```

   However, you **should install the version that matches your system and CUDA version** by following the official instructions here:  
   [https://pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/)

7. **Configure constants:**
   - Fill in any missing values in `constants.py`. You'll have to create a [`Mailjet`](https://www.mailjet.com/) account and get an API key and secret key.

8. **Prepare model directories:**
   - Create an `llms` folder in the project root and download [`solar-10.7b-instruct`](https://huggingface.co/TheBloke/SOLAR-10.7B-Instruct-v1.0-GGUF).
   - Create `image_generation/models` folder and download the image generation model [`sdxl_lightning_2step_unet`](https://huggingface.co/ByteDance/SDXL-Lightning).

   Using other models is also possible with slight modifications to the code.

9. **Start RabbitMQ:**
   ```bash
   docker run -d --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4.0-management
   ```

10. **Run the backend core service:**
    ```bash
    python app.py
    ```

11. **Set up SearXNG (for private web search):**
    - Edit `searxng-docker/searxng/settings.yml` and update the `secret_key`.
    - Start the service:
      ```bash
      cd searxng-docker
      docker-compose up -d
      ```

12. **Start additional services:**
    - Image generation:
      ```bash
      cd image_generation
      faststream run image_generation:app
      ```
    - Text-to-speech:
      ```bash
      cd Kokoro-TTS-Local
      faststream run tts:app
      ```
