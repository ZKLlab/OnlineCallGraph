FROM ubuntu:16.04

MAINTAINER ZKLlab <zkl@zkllab.com>

ENV PYTHONBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

COPY sources.list /etc/apt/sources.list
RUN apt-get update && apt-get install -y wget cflow graphviz \
    python2.7 python-pip python-dev uwsgi-plugin-python nginx supervisor
COPY nginx/flask.conf /etc/nginx/sites-available/
COPY supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY app /var/www/app

RUN mkdir -p /var/log/nginx/app /var/log/uwsgi/app /var/log/supervisor \
    /var/www/app/call_graph /var/www/app/static \
    && rm /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/flask.conf /etc/nginx/sites-enabled/flask.conf \
    && echo "daemon off;" >> /etc/nginx/nginx.conf \
    && pip install -r /var/www/app/requirements.txt \
    && chown -R www-data:www-data /var/www/app \
    && chown -R www-data:www-data /var/log

EXPOSE 5050

WORKDIR /var/www/app
CMD ["/usr/bin/supervisord"]