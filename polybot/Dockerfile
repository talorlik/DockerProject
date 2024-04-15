# Official Python runtime as a parent image
FROM python:alpine3.19 AS compile-image
RUN apk add --update --no-cache python3-dev build-base linux-headers pcre-dev

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the requirements into the container
COPY python/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

FROM python:alpine3.19 AS build-image
RUN apk add --update --no-cache pcre-dev
# Create a group and user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy the environment and changing the permissions to allow for non root user
COPY --from=compile-image --chown=appuser:appgroup /opt/venv /opt/venv

# Set the working directory in the container
WORKDIR /app
COPY . .
RUN chown -R appuser:appgroup /app

# Tell docker that all future commands should run as the appuser user
USER appuser

# Make port 8443 available to the world outside this container
EXPOSE 8443

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

CMD ["uwsgi", "--ini", "/app/uwsgi.ini"]