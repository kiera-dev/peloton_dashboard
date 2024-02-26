FROM python:3.9
EXPOSE 8080

# Set environment variables directly
ENV PELOTON_USERNAME=${PELOTON_USERNAME} \
    PELOTON_PASSWORD=${PELOTON_PASSWORD} \
    GOOGLE_APPLICATION_CREDENTIALS="/app/keyfile.json"

WORKDIR /app

# Install Google Cloud SDK
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-sdk

# Install application dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . .

CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]



# ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]


# fyi local cmds: 
# docker build --build-arg PELOTON_USERNAME=<username> --build-arg PELOTON_PASSWORD=<password> -t my_streamlit_app .
# docker run -p 8501:8501 my_streamlit_app