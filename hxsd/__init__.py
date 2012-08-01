#!/usr/bin/python

import socket
import struct
import threading
import time


class service(object):
    """Stores variables for a service"""
    def __init__(self, serviceName, servicePort, serviceIP=""):
        self.serviceName = serviceName
        self.servicePort = servicePort
        self.serviceIP = serviceIP

    def __repr__(self):
        return "%s %s:%s" % (self.serviceName,
                str(self.serviceIP),
                self.servicePort)


class serviceFinder(object):
    """Find Services using the magic of multicast"""
    def __init__(self, ip, port):
        self.group = (ip, port)
        self.sock = socket.socket(socket.AF_INET,
                socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.IPPROTO_IP,
                socket.IP_MULTICAST_TTL,
                struct.pack('b', 33))
        self.sock.setsockopt(socket.SOL_IP,
                socket.IP_MULTICAST_LOOP,
                1)

    def search(self, serviceName):
        """
        Search for services using multicast sends out a request for services
        of the specified name and then waits and gathers responses
        """
        print("Searching for service '%s'" % serviceName)
        self.sock.settimeout(5)
        msg = "|".join(("findservice", serviceName))
        self.sock.sendto(msg.encode('ascii'), self.group)
        servicesFound = []
        while True:
            try:
                data, server = self.sock.recvfrom(1024)
                data = data.decode('ascii').split("|")
                cmd = data[0]
                servicePort = int(data[1])
                if cmd == "service":
                    servicesFound.append(
                            service(
                                serviceName,
                                servicePort,
                                serviceIP=server[0]))
            except socket.timeout:
                break
        return servicesFound


class serviceProvider(object):
    """A simple multicast listener which responds to
    requests for services it has"""
    def __init__(self, group, port):
        self.serverAddr = ('0.0.0.0', port)
        self.sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.serverAddr)

        mreq = struct.pack("=4sl", socket.inet_aton(group), socket.INADDR_ANY)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 1)
        self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
        self.services = {}
        self.exit = False

        self.listener = threading.Thread(target=self.listenerThread)

    def start(self):
        self.listener.start()

    def stop(self):
        self.exit = True

    def addService(self, serv):
        if serv.serviceName not in self.services:
            self.services[serv.serviceName] = serv

    def listenerThread(self):
        self.sock.setblocking(0)
        while True:
            if self.exit == True:
                break
            else:
                time.sleep(1)
                try:
                    data, address = self.sock.recvfrom(1024)
                except:
                    continue
                data = data.decode('ascii').split("|")
                if len(data) == 2:
                    cmd = data[0]
                    serviceName = data[1]
                    if cmd == "findservice":
                        if serviceName in self.services:
                            ourServicePort = self.services[serviceName].servicePort
                            msg = "|".join(("service", str(ourServicePort)))
                            self.sock.sendto(msg.encode('ascii'), address)


def main():
    import sys
    if len(sys.argv) == 1:
        print("Usage: hxsd [provide|search]")
        sys.exit(1)

    if sys.argv[1] == 'provide':
        if len(sys.argv) < 4:
            print("Usage: hxsd provide [service] [port]")
            exit()
        derpService = service(sys.argv[2], sys.argv[3])
        provider = serviceProvider('224.3.29.110', 9990)
        provider.addService(derpService)
        provider.start()
    elif sys.argv[1] == 'search':
        if len(sys.argv) < 3:
            print("usage: hxsd search [service]")
            exit()
        finder = serviceFinder('224.3.29.110', 9990)
        print(finder.search(sys.argv[2]))

if __name__ == "__main__":
    main()

