# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install sudo, Docker, and Make
RUN apt-get update && apt-get install -y sudo docker.io make


# Set the working directory in the container
WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port on which the application might run (adjust as needed)
EXPOSE 5000

# Run script.py when the container launches
CMD ["python3", "load_balancer.py"]
