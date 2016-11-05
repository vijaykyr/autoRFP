#Build from nodejs slim image
FROM node:7.0-slim

# Install APT packages
RUN apt-get update && apt-get install -y \
    python2.7 \
    python-pip \
    git

#Download app code
RUN git clone https://github.com/vijaykyr/rfi-o-matic.git

#Expose private port inside container (bind to public port N using 'docker run -p N:8081')
EXPOSE 80