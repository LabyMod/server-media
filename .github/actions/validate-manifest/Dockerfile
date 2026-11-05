FROM python:3.12-slim

COPY ./ /

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "/validate.py"]
