publish-build:
	uv build

publish-clean:
	rm -rf dist/

# Release: tag the current version and push to trigger CI publish.
release:
	@VERSION=$$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'); \
	echo "Releasing v$$VERSION"; \
	git tag "v$$VERSION"; \
	git push origin "v$$VERSION"
