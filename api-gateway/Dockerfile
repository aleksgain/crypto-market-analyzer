FROM golang:1.20

WORKDIR /app

# Copy everything needed
COPY . .

# Download dependencies
RUN go mod download

# Build the application
RUN go build -o /app/api-gateway .

# Verify the binary exists
RUN ls -la /app/api-gateway
RUN chmod +x /app/api-gateway

# Expose port
EXPOSE 8080

# Start the application
CMD ["/app/api-gateway"] 