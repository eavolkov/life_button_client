import random
import datetime

from twisted.internet import reactor, protocol, task

from settings import LOCATION_PERIOD, KEEPALIVE_PERIOD, SERVER_HOST, SERVER_PORT, ACK_MAX_TIMEOUT


class Protocol(protocol.Protocol):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.device_id = random.randint(0, 1e8)
        self.wait_ack = False
        self.wait_ack_since = None

    def connectionMade(self):
        print('Connected')
        self._send_with_ack(f'cmd_id {self.device_id}')
        task.LoopingCall(self.send_location).start(LOCATION_PERIOD)
        task.LoopingCall(self.send_keepalive).start(KEEPALIVE_PERIOD)
    
    def dataReceived(self, data):
        if self.wait_ack and data.decode().strip() == 'ack':
            self.wait_ack = False
            print('Received: ack')

    def check_ack(self):
        if self.wait_ack:
            delay = datetime.datetime.now() - self.wait_ack_since
            if delay.seconds > ACK_MAX_TIMEOUT:
                print('Reconnect')
            else:
                return True
        return False

    def send_location(self):
        lat, lng = self._random_geo()
        self._send_with_ack(f'cmd_location {lat} {lng}')

    def send_keepalive(self):
        self._send_with_ack('cmd_keepalive')

    @staticmethod
    def _random_geo():
        return random.uniform(0, 180), random.uniform(0, 90)

    def _send_with_ack(self, command):
        if self.check_ack():
            return

        if isinstance(command, str):
            command = command.encode()

        print(f'Send: {command.decode()}')

        self.transport.write(command)
        self.wait_ack = True
        self.wait_ack_since = datetime.datetime.now()

class ClientFactory(protocol.ClientFactory):
    protocol = Protocol


if __name__ == '__main__':
    reactor.connectTCP(SERVER_HOST, SERVER_PORT, ClientFactory())
    reactor.run()
