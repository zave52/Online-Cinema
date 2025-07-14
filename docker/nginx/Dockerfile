FROM nginx:latest
LABEL authors="zakhar"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apache2-utils \
        bash && \
    rm -rf /var/lib/apt/lists/*

COPY ./scripts/set_nginx_basic_auth.sh /scripts/set_nginx_basic_auth.sh

RUN chmod +x /scripts/*.sh

ENTRYPOINT [ "/scripts/set_nginx_basic_auth.sh" ]

CMD [ "nginx", "-g", "daemon off;" ]
