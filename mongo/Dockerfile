# Use the official MongoDB image
FROM mongo:5

# Copy the initialization script into the container
COPY init-script.sh /usr/local/bin/init-script.sh
RUN chmod +x /usr/local/bin/init-script.sh

# Set the command to run the script
CMD ["/usr/local/bin/init-script.sh"]
