FROM mysql:8.0-debian

COPY deploy.sh /always-initdb.d/
COPY . /app
WORKDIR /app

RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y python3-pip

RUN pip install --upgrade pip --break-system-packages
RUN pip install -r requirements.txt --break-system-packages
RUN chmod +x /app/custom-entry.sh

ENV USER=theuser
RUN adduser --home /home/$USER --disabled-password --gecos GECOS $USER \
  && chsh -s /bin/zsh $USER
RUN chown -R $USER /app

USER $USER
ENV HOME=/home/$USER
ENV MYSQL_ROOT_PASSWORD="mysql1234"

EXPOSE 5000

ENTRYPOINT ["/app/custom-entry.sh"]
CMD ["mysqld"]