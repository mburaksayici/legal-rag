# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
libgl1 \
libglib2.0-0 \
libsm6 \
libxext6 \
libxrender-dev \
libjpeg-dev \
zlib1g-dev \
libpng-dev \
libtiff-dev \
libavcodec-dev \
libavformat-dev \
libswscale-dev \
libv4l-dev \
tesseract-ocr \
poppler-utils \
&& apt-get clean && rm -rf /var/lib/apt/lists/*


RUN apt-get update && apt-get install -y poppler-utils tesseract-ocr libtesseract-dev


# Install uv
RUN pip install uv

# Copy pyproject.toml and uv.lock first for better caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
RUN uv sync --frozen

# Download spaCy model
RUN uv run python -m spacy download en_core_web_sm



RUN uv run python -m nltk.downloader punkt_tab punkt averaged_perceptron_tagger \
    && uv run python -m nltk.downloader -d /usr/local/share/nltk_data stopwords

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000 5555

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
