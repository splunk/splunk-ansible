# This script is based on the one availible from dockerdocs: https://docs.docker.com/engine/examples/running_ssh_service/

FROM debian:buster

RUN apt update && apt install -y openssh-server python-minimal
RUN mkdir /var/run/sshd
RUN echo 'root:screencast' | chpasswd
RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PermitRootLogin yes/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

#these are required for splunk to start inside a container
VOLUME [ "/opt/splunk/etc", "/opt/splunk/var" ]

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]
