FROM alpine
RUN apk add --no-cache imagemagick bash
COPY validate.sh /validate.sh
RUN chmod +x /validate.sh
ENTRYPOINT ["/validate.sh"]