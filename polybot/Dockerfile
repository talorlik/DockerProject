# Initial stage for building the application
FROM python:alpine3.19 AS build-stage
# Install build dependencies
RUN apk add --no-cache build-base linux-headers musl-dev python3-dev libffi-dev gcc

# Set up a virtual environment to isolate package installations
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the requirements file
COPY python/requirements.txt .

# Install requirements using pip
RUN pip3 install --no-cache-dir -r requirements.txt

# Build the final image without the build dependencies
FROM python:alpine3.19
# Install runtime libraries
RUN apk add --no-cache libstdc++
# Copy the virtual environment from the build stage
COPY --from=build-stage /opt/venv /opt/venv
# Set the virtual environment path
ENV PATH="/opt/venv/bin:$PATH"
# Add the python directory
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/python"
# Set the working dir and copy application code
WORKDIR /app
COPY . .

# Create a non-root user and switch to it
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN chown -R appuser:appgroup /app
USER appuser

# Expose the port that the app runs on
EXPOSE 8443

# Command to run the app
CMD ["uwsgi", "--ini", "uwsgi.ini"]
