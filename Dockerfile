#Build from nodejs slim image
FROM node:7.0-slim

# Install APT packages
RUN apt-get update && apt-get install -y \
    python2.7 \
    python-pip \
    git

#Download app code
RUN git clone https://github.com/vijaykyr/rfi-o-matic.git

#Change working directory
WORKDIR /rfi-o-matic

#Networking settings
EXPOSE 8080 
#VM routes requests to port 8080 by default (can change this in app.yaml)

#Start web server
CMD ["node", "express_server.js"]