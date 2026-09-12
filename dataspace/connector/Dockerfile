# Use the latest stable version of openjdk and Debian
FROM eclipse-temurin:17-jre-jammy

# Update package lists and install curl
# The --no-install-recommends flag helps keep the image small
RUN apt-get update && apt-get install --no-install-recommends curl -y

WORKDIR /app

# Copy the JAR file and other resources
COPY ./build/libs/connector.jar /app/connector.jar
# If you need to copy the resources directory, uncomment the line below.
# COPY ./resources /resources

# Set the environment variable. Note the correct format without spaces.
ENV EDC_FS_CONFIG="/resources/config.properties"

# Define the entrypoint to run the JAR file
ENTRYPOINT ["java", "-jar", "connector.jar"]