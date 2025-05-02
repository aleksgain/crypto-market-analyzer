FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# Clear ALL proxy settings before installing anything
ENV http_proxy=""
ENV https_proxy=""
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""
ENV no_proxy=""
ENV NO_PROXY=""
# Also clear Python-specific proxy settings
ENV PYTHONHTTPSVERIFY=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1
ENV REQUESTS_CA_BUNDLE=""

# Install dependencies in the correct order
RUN pip install --no-cache-dir numpy==1.24.3
RUN pip install --no-cache-dir werkzeug==2.2.3
RUN pip install --no-cache-dir flask==2.2.3
RUN pip install --no-cache-dir -r requirements.txt
# Ensure openai is properly installed with the right version
RUN pip uninstall -y openai && pip install --no-cache-dir openai==1.6.0

COPY . .

# Download NLTK data for sentiment analysis
RUN python -c "import nltk; nltk.download('vader_lexicon')"

EXPOSE 5000

CMD ["python", "app.py"] 