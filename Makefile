up:
	docker compose up -d

clean:
	docker compose down

# Define the image name
IMAGE_NAME=selenium-fetcher

# Target to build the Docker image
.PHONY: build
build:
	docker build -t $(IMAGE_NAME) .

# Target to run the Docker container
.PHONY: run
run:
	docker run --rm $(IMAGE_NAME)
