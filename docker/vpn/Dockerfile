FROM alpine:3.19

# OpenVPN + bash + iproute2 + iptables
RUN apk add --no-cache openvpn bash iproute2 iptables coreutils

COPY entrypoint.sh        /entrypoint.sh
COPY entrypoint-multi.sh  /entrypoint-multi.sh
RUN chmod +x /entrypoint.sh /entrypoint-multi.sh

ARG ENTRYPOINT=entrypoint.sh
ENTRYPOINT ["/${ENTRYPOINT}"]
