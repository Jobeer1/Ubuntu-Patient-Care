FROM python:3.11

RUN pip install uvicorn
RUN pip install fastapi==0.103.0

RUN mkdir /auth-service
COPY *.py /auth-service

WORKDIR /auth-service
ENTRYPOINT [ "uvicorn", "auth_service:app", "--host", "0.0.0.0", "--port", "8020"]

