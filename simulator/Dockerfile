FROM python:3.13.7-slim-bookworm
WORKDIR /app
COPY server.py .
USER 1000:1000
EXPOSE 8081
CMD ["python","-u","server.py"]
