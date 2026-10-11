FROM alpine
RUN apk add --no-cache imagemagick imagemagick-jpeg bash python3 py3-pillow
COPY validate.sh /validate.sh
COPY edges.py /edges.py
RUN chmod +x /validate.sh
ENTRYPOINT ["/validate.sh"]