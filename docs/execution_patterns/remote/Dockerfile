# This script is based on the one availible from dockerdocs: https://docs.docker.com/engine/examples/running_ssh_service/

FROM ubuntu

RUN apt update && \
	apt install -y openssh-server sudo

RUN mkdir /var/run/sshd && \
	echo 'root:screencast' | chpasswd && \
	sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
	sed -i 's/#PermitRootLogin yes/PermitRootLogin yes/' /etc/ssh/sshd_config && \
	echo "SSH login fix. Otherwise user is kicked off after login" && \
	sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd && \
	echo "Setup passwordless sudo access" && \
	sed -i 's/^%sudo.*/%sudo ALL=(ALL) NOPASSWD: ALL/g' /etc/sudoers

RUN groupadd -r splunk && \
	useradd -r -m -g splunk splunk && \
	usermod -aG sudo splunk

EXPOSE 2222
CMD ["/usr/sbin/sshd", "-D", "-p", "2222"]
