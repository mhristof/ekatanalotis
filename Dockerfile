# Use official Python image based on Ubuntu as the base
FROM python:3

# Install necessary packages
RUN apt-get update && apt-get install -y wget default-jre-headless && \
    apt-get clean

# Install Selenium
RUN pip install selenium

# Download ChromeDriver - adjust version as needed
RUN wget -q -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/94.0.4606.41/chromedriver_linux64.zip && \
    unzip -o /tmp/chromedriver.zip -d /usr/local/bin && \
    rm /tmp/chromedriver.zip

# Set environment variables
ENV DISPLAY=:99

# Copy the Python script into the container
COPY fetch_data.py /usr/src/

# Command to run the Python script
CMD ["python", "/usr/src/fetch_data.py"]
