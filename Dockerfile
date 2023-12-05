FROM python:3.9.0
WORKDIR /websocketserver
COPY . ./
RUN pip install django==4.0.4 && pip install channels==3.0.4
RUN pip install pyjwt==2.4.0 && pip install channels-redis==3.4.0
RUN pip install requests==2.27.1 && pip install djangorestframework==3.13.1
RUN pip install redis==4.3.3 && pip install psycopg2==2.9.3
RUN pip install schedule==1.1.0
ARG DJANGO_SETTINGS_MODULE=websocketserver.settings.prod
CMD ["python", "./manage.py", "runserver", "0.0.0.0:8000"]
EXPOSE 8000

