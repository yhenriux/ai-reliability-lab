FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir 'streamlit>=1.38,<2' 'pandas>=2.1,<3'
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
