# Use the latest stable version of openjdk and Debian
FROM eclipse-temurin:21-jre-jammy

# Update package lists and install curl
# The --no-install-recommends flag helps keep the image small
RUN apt-get update && apt-get install --no-install-recommends curl -y

WORKDIR /app

# Copy the JAR file from the connector build directory
COPY connector/build/libs/connector.jar /app/connector.jar

# Define the entrypoint to run the JAR file with config
ENTRYPOINT ["java", "-Dedc.fs.config=/resources/config.properties", "-jar", "connector.jar"]