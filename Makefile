IMAGE_NAME:=empata-reserva:test

run:
	docker buildx build \
		--platform linux/amd64 \
		--provenance=false \
		-t ${IMAGE_NAME} .

	docker run \
		--platform linux/amd64 \
		-p 9000:8080 \
		--env-file .env \
		${IMAGE_NAME}

invoke:
	curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'