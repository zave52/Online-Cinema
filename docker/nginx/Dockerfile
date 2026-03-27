FROM nginx:1.28.3-alpine3.23-perl
LABEL authors="zakhar"

RUN apk add --no-cache  \
    apache2-utils  \
    bash

COPY ./scripts/set_nginx_basic_auth.sh /scripts/set_nginx_basic_auth.sh

ENTRYPOINT [ "/scripts/set_nginx_basic_auth.sh" ]

CMD [ "nginx", "-g", "daemon off;" ]
