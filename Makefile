REGISTRY=ghcr.io
IMAGE_NAME=$(error $(patsubst https://github.com/%.git,%,$(shell git remote get-url origin)))

image:
	docker build -t ${REGISTRY}/${IMAGE_NAME}:edge .
