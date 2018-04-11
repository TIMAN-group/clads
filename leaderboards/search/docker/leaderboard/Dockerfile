FROM python:3
RUN mkdir -p /srv/leaderboard
WORKDIR /srv/leaderboard
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:app"]
