# Copyright (c) 2007-2009, Mamta Singh. All rights reserved. see README for details.
# Copyright (c) 2010-2011, Kundan Singh.

import os
import sys
import time
import struct
import socket
import traceback
try:
    from rtmplite3 import multitask, amf # try import from package
    from rtmplite3.flv import FLV
    from rtmplite3.common import truncate, Header, Message, Command
except:
    try:
        import multitask, amf
        from flv import FLV
        from common import truncate, Header, Message, Command
    except:
        exit("Required module not found")
import hashlib
import hmac
import random

_debug = _verbose = _recording = False
_version, _build = "v0.3.5", "20210528"


class ConnectionClosed(Exception):
    'raised when the client closed the connection'


class SockStream(object):
    '''A class that represents a socket as a stream'''

    def __init__(self, sock):
        self.sock, self.buffer = sock, b''
        self.bytesWritten = self.bytesRead = 0

    def close(self):
        self.sock.close()

    def read(self, count):
        try:
            while True:
                if len(self.buffer) >= count:  # do have enough data in buffer
                    data, self.buffer = self.buffer[:count], self.buffer[count:]
                    return(data)
                if _verbose:
                    print(f'socket.read[{count}] calling recv()')
                # read more from socket
                data = (yield multitask.recv(self.sock, 4096))
                if not data:
                    raise ConnectionClosed
                if _verbose:
                    print(f'socket.read[{len(data)}] {truncate(data)}')
                self.bytesRead = self.bytesRead + len(data)
                self.buffer = self.buffer + data
        except Exception as e:
            if _debug:
                print(e)
            # anything else is treated as connection closed.
            raise ConnectionClosed

    def unread(self, data):
        self.buffer = data + self.buffer

    def write(self, data):
        while len(data) > 0:  # write in 4K chunks each time
            chunk, data = data[:4096], data[4096:]
            self.bytesWritten = self.bytesWritten + len(chunk)
            if _verbose:
                print(f'socket.write[{len(chunk)}] {truncate(chunk)}' )
            try:
                yield multitask.send(self.sock, chunk)
            except BaseException:
                raise ConnectionClosed


class Protocol(object):
    PING_SIZE, DEFAULT_CHUNK_SIZE, HIGH_WRITE_CHUNK_SIZE, PROTOCOL_CHANNEL_ID = 1536, 128, 4096, 2  # constants
    READ_WIN_SIZE, WRITE_WIN_SIZE = 5000000, 5000000

    def __init__(self, sock):
        self.stream = SockStream(sock)
        self.lport = sock.getsockname()[1]
        self.lastReadHeaders, self.incompletePackets, self.lastWriteHeaders = dict(), dict(), dict()
        self.readChunkSize = self.writeChunkSize = Protocol.DEFAULT_CHUNK_SIZE
        self.readWinSize0, self.readWinSize, self.writeWinSize0, self.writeWinSize = 0, self.READ_WIN_SIZE, 0, self.WRITE_WIN_SIZE
        self.nextChannelId = Protocol.PROTOCOL_CHANNEL_ID + 1
        self._time0 = time.time()
        self.writeQueue = multitask.Queue()

    @property
    def relativeTime(self):
        return int(1000 * (time.time() - self._time0))

    def messageReceived(self, msg):  # override in subclass
        yield

    def protocolMessage(self, msg):
        if msg.type == Message.ACK:  # respond to ACK requests
            self.writeWinSize0 = struct.unpack('>L', msg.data)[0]
#            response = Message()
#            response.type, response.data = msg.type, msg.data
#            yield self.writeMessage(response)
        elif msg.type == Message.CHUNK_SIZE:
            self.readChunkSize = struct.unpack('>L', msg.data)[0]
            if _debug:
                print(f"set read chunk size to {self.readChunkSize}")
        elif msg.type == Message.WIN_ACK_SIZE:
            self.readWinSize, self.readWinSize0 = struct.unpack(
                '>L', msg.data)[0], self.stream.bytesRead
        elif msg.type == Message.USER_CONTROL:
            type, data = struct.unpack('>H', msg.data[:2])[0], msg.data[2:]
            if type == 3:  # client expects a response when it sends set buffer length
                streamId, bufferTime = struct.unpack('>II', data)
                response = Message()
                response.time, response.type, response.data = self.relativeTime, Message.USER_CONTROL, struct.pack(
                    '>HI', 0, streamId)
                yield self.writeMessage(response)
        yield

    def connectionClosed(self):
        yield

    def parse(self):
        try:
            yield self.parseCrossDomainPolicyRequest()  # check for cross domain policy
            yield self.parseHandshake()  # parse rtmp handshake
            yield self.parseMessages()   # parse messages
        except ConnectionClosed:
            if _debug:
                print('parse connection closed')
            yield self.connectionClosed()
        except BaseException:
            if _debug:
                print('exception, closing connection')
                traceback.print_exc()
            yield self.connectionClosed()

    def writeMessage(self, message):
        yield self.writeQueue.put(message)

    def parseCrossDomainPolicyRequest(self):
        # read the request
        REQUEST = b'<policy-file-request/>\x00'
        data = (yield self.stream.read(len(REQUEST)))
        if data == REQUEST:
            if _debug:
                print(data)
            data = b'''<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">
                    <cross-domain-policy>
                      <allow-access-from domain="*" to-ports="%s" secure='false'/>
                    </cross-domain-policy>''' % self.lport
            yield self.stream.write(data)
            raise ConnectionClosed
        else:
            yield self.stream.unread(data)

    SERVER_KEY = b'\x47\x65\x6e\x75\x69\x6e\x65\x20\x41\x64\x6f\x62\x65\x20\x46\x6c\x61\x73\x68\x20\x4d\x65\x64\x69\x61\x20\x53\x65\x72\x76\x65\x72\x20\x30\x30\x31\xf0\xee\xc2\x4a\x80\x68\xbe\xe8\x2e\x00\xd0\xd1\x02\x9e\x7e\x57\x6e\xec\x5d\x2d\x29\x80\x6f\xab\x93\xb8\xe6\x36\xcf\xeb\x31\xae'
    FLASHPLAYER_KEY = b'\x47\x65\x6E\x75\x69\x6E\x65\x20\x41\x64\x6F\x62\x65\x20\x46\x6C\x61\x73\x68\x20\x50\x6C\x61\x79\x65\x72\x20\x30\x30\x31\xF0\xEE\xC2\x4A\x80\x68\xBE\xE8\x2E\x00\xD0\xD1\x02\x9E\x7E\x57\x6E\xEC\x5D\x2D\x29\x80\x6F\xAB\x93\xB8\xE6\x36\xCF\xEB\x31\xAE'

    def parseHandshake(self):
        '''Parses the rtmp handshake'''
        data = (yield self.stream.read(Protocol.PING_SIZE + 1))  # bound version and first ping
        if _debug:
            print(f'socket.read[{len(data)}] {truncate(data)}')
        data = Protocol.handshakeResponse(data)
        yield self.stream.write(data)
        data = (yield self.stream.read(Protocol.PING_SIZE))

    @staticmethod
    def handshakeResponse(data):
        # send both data parts before reading next ping-size, to work with
        # ffmpeg
        if struct.unpack('>I', data[5:9])[0] == 0:
            data = b'\x03' + b'\x00' * Protocol.PING_SIZE
            return data + data[1:]
        else:
            chunk_type, data = data[0], data[1:]  # first byte is ignored
            scheme = None
            for s in range(0, 2):
                digest_offset = (sum([data[i] for i in range(772, 776)]) %
                                    728 + 776) if s == 1 else (sum([data[i] \
                                    for i in range(8, 12)]) % 728 + 12)
                temp = data[0:digest_offset] + \
                    data[digest_offset + 32:Protocol.PING_SIZE]
                hash = Protocol._calculateHash(
                    temp, Protocol.FLASHPLAYER_KEY[:30])
                if hash == data[digest_offset:digest_offset + 32]:
                    scheme = s
                    break
            if scheme is None:
                if _debug:
                    print('invalid RTMP connection data, assuming scheme 0')
                scheme = 0
            client_dh_offset = Protocol._calculate_offset_1(data, scheme)
            outgoingKp = data[client_dh_offset:client_dh_offset + 128]
            handshake = struct.pack(
                '>IBBBB', 0, 1, 2, 3, 4) + os.urandom(Protocol.PING_SIZE - 8)
            server_dh_offset = Protocol._calculate_offset_1(handshake, scheme)
            keys = Protocol._generateKeyPair()  # (public, private)
            handshake = handshake[:server_dh_offset] + \
                keys[0][0:128] + handshake[server_dh_offset + 128:]
            if chunk_type > 0x03:
                raise ValueError('RTMP encryption is not supported')
            server_digest_offset = Protocol._calculate_offset_2(handshake, scheme)
            temp = handshake[0:server_digest_offset] + \
                handshake[server_digest_offset + 32:Protocol.PING_SIZE]
            hash = Protocol._calculateHash(temp, Protocol.SERVER_KEY[:36])
            handshake = handshake[:server_digest_offset] + \
                hash + handshake[server_digest_offset + 32:]
            buffer = data[:Protocol.PING_SIZE - 32]
            key_challenge_offset = Protocol._calculate_offset_2(buffer, scheme)
            challenge_key = data[key_challenge_offset:key_challenge_offset + 32]
            hash = Protocol._calculateHash(
                challenge_key, Protocol.SERVER_KEY[:68])
            rand_bytes = os.urandom(Protocol.PING_SIZE - 32)
            last_hash = Protocol._calculateHash(rand_bytes, hash[:32])
            output = chr(chunk_type).encode(encoding="utf-8") + \
                handshake + rand_bytes + last_hash
            return output

    @staticmethod
    def _calculateHash(msg, key):  # Hmac-sha256
        return hmac.new(key, msg, hashlib.sha256).digest()
    
    @staticmethod
    def _calculate_offset_1(data, scheme):
        return (sum([data[i] for i in range(768, 772)]) %
                    632 + 8) if scheme == 1 else (sum([data[i] \
                    for i in range(1532, 1536)]) % 632 + 772)

    @staticmethod
    def _calculate_offset_2(data, scheme):
        return (sum([data[i] for i in range(772, 776)]) %
                    728 + 776) if scheme == 1 else (sum([data[i] \
                    for i in range(8, 12)]) % 728 + 12)

    @staticmethod
    def _generateKeyPair():  # dummy key pair since we don't support encryption
        return (os.urandom(128), '')

    def parseMessages(self):
        '''Parses complete messages until connection closed. Raises ConnectionLost exception.'''
        CHANNEL_MASK = 0x3F
        while True:
            hdrsize = (yield self.stream.read(1))[0]  # read header size byte
            channel = hdrsize & CHANNEL_MASK
            if channel == 0:  # we need one more byte
                channel = 64 + (yield self.stream.read(1))[0]
            elif channel == 1:  # we need two more bytes
                data = (yield self.stream.read(2))
                channel = 64 + data[0] + 256 * data[1]

            hdrtype = hdrsize & Header.MASK   # read header type byte
            if hdrtype == Header.FULL or channel not in self.lastReadHeaders:
                header = Header(channel)
                self.lastReadHeaders[channel] = header
            else:
                header = self.lastReadHeaders[channel]

            if hdrtype < Header.SEPARATOR:  # time or delta has changed
                data = (yield self.stream.read(3))
                header.time = struct.unpack('!I', b'\x00' + data)[0]

            if hdrtype < Header.TIME:  # size and type also changed
                data = (yield self.stream.read(3))
                header.size = struct.unpack('!I', b'\x00' + data)[0]
                header.type = (yield self.stream.read(1))[0]

            if hdrtype < Header.MESSAGE:  # streamId also changed
                data = (yield self.stream.read(4))
                header.streamId = struct.unpack('<I', data)[0]

            if header.time == 0xFFFFFF:  # if we have extended timestamp, read it
                data = (yield self.stream.read(4))
                header.extendedTime = struct.unpack('!I', data)[0]
                if _debug:
                    print('extended time stamp:', header.extendedTime)
            else:
                header.extendedTime = None

            if hdrtype == Header.FULL:
                header.currentTime = header.extendedTime or header.time
                header.hdrtype = hdrtype
            elif hdrtype in (Header.MESSAGE, Header.TIME):
                header.hdrtype = hdrtype

            # print header.type, '0x%02x' % (hdrtype,), header.time,
            # header.currentTime

            # if _debug: print 'R', header, header.currentTime,
            # header.extendedTime, '0x%x' % (hdrsize,)

            # are we continuing an incomplete packet?
            data = self.incompletePackets.get(channel, b"")

            count = min(header.size - (len(data)),
                        self.readChunkSize)  # how much more

            data = data + (yield self.stream.read(count))

            # check if we need to send Ack
            if self.readWinSize is not None:
                if self.stream.bytesRead > (
                        self.readWinSize0 + self.readWinSize):
                    self.readWinSize0 = self.stream.bytesRead
                    ack = Message()
                    ack.time, ack.type, ack.data = self.relativeTime, Message.ACK, struct.pack(
                        '>L', self.readWinSize0)
                    yield self.writeMessage(ack)

            if len(data) < header.size:  # we don't have all data
                self.incompletePackets[channel] = data
            else:  # we have all data
                if hdrtype in (Header.MESSAGE, Header.TIME):
                    header.currentTime = header.currentTime + \
                        (header.extendedTime or header.time)
                elif hdrtype == Header.SEPARATOR:
                    if header.hdrtype in (Header.MESSAGE, Header.TIME):
                        header.currentTime = header.currentTime + \
                            (header.extendedTime or header.time)
                if len(data) == header.size:
                    if channel in self.incompletePackets:
                        del self.incompletePackets[channel]
                        if _verbose:
                            print(f'aggregated {len(data)} bytes message: readChunkSize({self.readChunkSize}) x {len(data) / self.readChunkSize}')
                else:
                    data, self.incompletePackets[channel] = data[:header.size], data[header.size:]

                hdr = Header(
                    channel=header.channel,
                    time=header.currentTime,
                    size=header.size,
                    type=header.type,
                    streamId=header.streamId)
                msg = Message(hdr, data)

                if hdr.type == Message.AGGREGATE:
                    ''' see http://code.google.com/p/red5/source/browse/java/server/trunk/src/org/red5/server/net/rtmp/event/Aggregate.java / getParts()
                    '''
                    if _verbose:
                        print('Protocol.parseMessages aggregated msg=', msg)
                    aggdata = data
                    while len(aggdata) > 0:
                        '''
                        type=1 byte
                        size=3 bytes
                        time=4 bytes
                        streamId= 4 bytes
                        data= size bytes
                        backPointer=4 bytes, value == size
                        '''
                        subtype = aggdata[0]
                        subsize = struct.unpack(
                            '!I', b'\x00' + aggdata[1:4])[0]
                        subtime = struct.unpack('!I', aggdata[4:8])[0]
                        substreamid = struct.unpack('<I', aggdata[8:12])[0]
                        subheader = Header(
                            channel,
                            time=subtime,
                            size=subsize,
                            type=subtype,
                            streamId=substreamid)  # TODO: set correct channel
                        aggdata = aggdata[11:]  # skip header
                        submsgdata = aggdata[:subsize]  # get message data
                        submsg = Message(subheader, submsgdata)

                        yield self.parseMessage(submsg)

                        aggdata = aggdata[subsize:]  # skip message data

                        backpointer = struct.unpack('!I', aggdata[0:4])[0]
                        if backpointer != subsize:
                            print(f'Warning aggregate submsg backpointer={backpointer} != {subsize}')
                        # skip back pointer, go to next message
                        aggdata = aggdata[4:]
                else:
                    yield self.parseMessage(msg)

    def parseMessage(self, msg):
        try:
            if _verbose:
                print('Protocol.parseMessage msg=', msg)
            if msg.header.channel == Protocol.PROTOCOL_CHANNEL_ID:
                yield self.protocolMessage(msg)
            else:
                yield self.messageReceived(msg)
        except BaseException:
            if _debug:
                print(
                    'Protocol.parseMessage exception',
                    (traceback and traceback.print_exc() or None))

    def write(self):
        '''Writes messages to stream'''
        while True:
            #            while self.writeQueue.empty(): (yield multitask.sleep(0.01))
            #            message = self.writeQueue.get() # TODO this should be used using multitask.Queue and remove previous wait.
            # TODO this should be used using multitask.Queue and remove
            # previous wait.
            message = yield self.writeQueue.get()
            if _verbose:
                print('Protocol.write msg=', message)
            if message is None:
                try:
                    # just in case TCP socket is not closed, close it.
                    self.stream.close()
                except BaseException:
                    pass
                break

            # get the header stored for the stream
            if message.streamId in self.lastWriteHeaders:
                header = self.lastWriteHeaders[message.streamId]
            else:
                if self.nextChannelId <= Protocol.PROTOCOL_CHANNEL_ID:
                    self.nextChannelId = Protocol.PROTOCOL_CHANNEL_ID + 1
                header, self.nextChannelId = Header(
                    self.nextChannelId), self.nextChannelId + 1
                self.lastWriteHeaders[message.streamId] = header
            if message.type < Message.AUDIO:
                header = Header(Protocol.PROTOCOL_CHANNEL_ID)

            # now figure out the header data bytes
            if header.streamId != message.streamId or header.time == 0 or message.time <= header.time:
                header.streamId, header.type, header.size, header.time, header.delta = message.streamId, message.type, message.size, message.time, message.time
                control = Header.FULL
            elif header.size != message.size or header.type != message.type:
                header.type, header.size, header.time, header.delta = message.type, message.size, message.time, message.time - header.time
                control = Header.MESSAGE
            else:
                header.time, header.delta = message.time, message.time - header.time
                control = Header.TIME

            hdr = Header(
                channel=header.channel,
                time=header.delta if control in (
                    Header.MESSAGE,
                    Header.TIME) else header.time,
                size=header.size,
                type=header.type,
                streamId=header.streamId)
            assert message.size == len(message.data)

            data = b''
            while len(message.data) > 0:
                data = data + hdr.toBytes(control)  # gather header bytes
                count = min(self.writeChunkSize, len(message.data))
                data = data + message.data[:count]
                message.data = message.data[count:]
                control = Header.SEPARATOR  # incomplete message continuation
            try:
                yield self.stream.write(data)
            except ConnectionClosed:
                yield self.connectionClosed()
            except BaseException:
                print(traceback.print_exc())


class Stream(object):
    '''The stream object that is used for RTMP stream.'''
    count = 0

    def __init__(self, client):
        self.client, self.id, self.name = client, 0, ''
        # so that it doesn't complain about missing attribute
        self.recordfile = self.playfile = None
        self.queue = multitask.Queue()
        self._name = 'Stream[' + str(Stream.count) + ']'
        Stream.count = Stream.count + 1
        if _debug:
            print(self, 'created')

    def close(self):
        if _debug:
            print(self, 'closing')
        if self.recordfile is not None:
            self.recordfile.close()
            self.recordfile = None
        if self.playfile is not None:
            self.playfile.close()
            self.playfile = None
        self.client = None  # to clear the reference


    def __repr__(self):
        return self._name

    def recv(self):
        '''Generator to receive new Message on this stream, or None if stream is closed.'''
        return self.queue.get()

    def send(self, msg):
        '''Method to send a Message or Command on this stream.'''
        if isinstance(msg, Command):
            msg = msg.toMessage()
        msg.streamId = self.id
        # if _debug: print self,'send'
        if self.client is not None:
            yield self.client.writeMessage(msg)


class Client(Protocol):
    '''The client object represents a single connected client to the server.'''

    def __init__(self, sock, server):
        Protocol.__init__(self, sock)
        self.server, self.agent, self.streams, self._nextCallId, self._nextStreamId, self.objectEncoding = \
            server, None, {}, 2, 1, 0.0
        self.queue = multitask.Queue()  # receive queue used by application
        multitask.add(self.parse())
        multitask.add(self.write())

    def recv(self):
        '''Generator to receive new Message (msg, arg) on this stream, or (None,None) if stream is closed.'''
        return self.queue.get()

    def connectionClosed(self):
        '''Called when the client drops the connection'''
        if _debug:
            'Client.connectionClosed'
        yield self.writeMessage(None)
        yield self.queue.put((None, None))

    def messageReceived(self, msg):
        if (msg.type == Message.RPC or msg.type ==
                Message.RPC3) and msg.streamId == 0:
            cmd = Command.fromMessage(msg)
            # if _debug: print 'rtmp.Client.messageReceived cmd=', cmd
            if cmd.name == 'connect':
                self.agent = cmd.cmdData
                if _debug:
                    print('connect',', '.join([f'{x}={getattr(self.agent,x)}' for x in 'app flashVer swfUrl tcUrl fpad capabilities\
                         audioCodecs videoCodecs videoFunction pageUrl objectEncoding'.split() if hasattr(self.agent,x)]))
                self.objectEncoding = self.agent.objectEncoding if hasattr(
                    self.agent, 'objectEncoding') else 0.0
                yield self.server.queue.put((self, cmd.args))  # new connection
            elif cmd.name == 'createStream':
                response = Command(
                    name='_result',
                    id=cmd.id,
                    tm=self.relativeTime,
                    type=self.rpc,
                    args=[
                        self._nextStreamId])
                yield self.writeMessage(response.toMessage())

                stream = Stream(self)  # create a stream object
                stream.id = self._nextStreamId
                self.streams[self._nextStreamId] = stream
                self._nextStreamId = self._nextStreamId + 1

                # also notify others of our new stream
                yield self.queue.put(('stream', stream))
            elif cmd.name == 'closeStream':
                assert msg.streamId in self.streams
                # notify closing to others
                yield self.streams[msg.streamId].queue.put(None)
                del self.streams[msg.streamId]
            else:
                # if _debug: print 'Client.messageReceived cmd=', cmd
                yield self.queue.put(('command', cmd))  # RPC call
        else:  # this has to be a message on the stream
            assert msg.streamId != 0
            assert msg.streamId in self.streams
            # if _debug: print self.streams[msg.streamId], 'recv'
            stream = self.streams[msg.streamId]
            if not stream.client:
                stream.client = self
            yield stream.queue.put(msg)  # give it to stream

    @property
    def rpc(self):
        # TODO: reverting r141 since it causes exception in setting self.rpc
        return Message.RPC if self.objectEncoding == 0.0 else Message.RPC3

    def accept(self):
        '''Method to accept an incoming client.'''
        response = Command()
        response.id, response.name, response.type = 1, '_result', self.rpc
        if _debug:
            print('Client.accept() objectEncoding=', self.objectEncoding)
        arg = amf.Object(
            level='status',
            code='NetConnection.Connect.Success',
            description='Connection succeeded.',
            fmsVer='rtmplite/8,2')
        if hasattr(self.agent, 'objectEncoding'):
            arg.objectEncoding, arg.details = self.objectEncoding, None
        response.setArg(arg)
        yield self.writeMessage(response.toMessage())

    def rejectConnection(self, reason=''):
        '''Method to reject an incoming client.'''
        response = Command()
        response.id, response.name, response.type = 1, '_error', self.rpc
        response.setArg(
            amf.Object(
                level='status',
                code='NetConnection.Connect.Rejected',
                description=reason,
                fmsVer='rtmplite/8,2',
                details=None))
        yield self.writeMessage(response.toMessage())

    def redirectConnection(self, url, reason='Connection failed'):
        '''Method to redirect an incoming client to the given url.'''
        response = Command()
        response.id, response.name, response.type = 1, '_error', self.rpc
        extra = dict(code=302, redirect=url)
        response.setArg(
            amf.Object(
                level='status',
                code='NetConnection.Connect.Rejected',
                description=reason,
                fmsVer='rtmplite/8,2',
                details=None,
                ex=extra))
        yield self.writeMessage(response.toMessage())

    def call(self, method, *args):
        '''Call a (callback) method on the client.'''
        cmd = Command()
        cmd.id, cmd.time, cmd.name, cmd.type = self._nextCallId, self.relativeTime, method, self.rpc
        cmd.args, cmd.cmdData = args, None
        self._nextCallId = self._nextCallId + 1
        if _debug:
            print(
                'Client.call method=',
                method,
                'args=',
                args,
                ' msg=',
                cmd.toMessage())
        yield self.writeMessage(cmd.toMessage())

    def createStream(self):
        ''' Create a stream on the server side'''
        stream = Stream(self)
        stream.id = self._nextStreamId
        self.streams[stream.id] = stream
        self._nextStreamId = self._nextStreamId + 1
        return stream


class Server(object):
    '''A RTMP server listens for incoming connections and informs the app.'''

    def __init__(self, sock):
        '''Create an RTMP server on the given bound TCP socket. The server will terminate
        when the socket is disconnected, or some other error occurs in listening.'''
        self.sock = sock
        self.queue = multitask.Queue()  # queue to receive incoming client connections
        multitask.add(self.run())

    def recv(self):
        '''Generator to wait for incoming client connections on this server and return
        (client, args) or (None, None) if the socket is closed or some error.'''
        return self.queue.get()

    def run(self):
        try:
            while True:
                # receive client TCP
                sock, remote = (yield multitask.accept(self.sock))
                if sock is None:
                    if _debug:
                        print('rtmp.Server accept(sock) returned None.')
                    break
                if _debug:
                    print('connection received from', remote)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # make it non-block
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) # Issue #106
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10) # Issue #106
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10) # Issue #106
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 2) # Issue #106
                client = Client(sock, self)
        except GeneratorExit:
            pass  # terminate
        except BaseException:
            if _debug:
                print(
                    'rtmp.Server exception ',
                    (sys and sys.exc_info() or None))

        if (self.sock):
            try:
                self.sock.close()
                self.sock = None
            except BaseException:
                pass
        if (self.queue):
            yield self.queue.put((None, None))
            self.queue = None


class App(object):
    '''An application instance containing any number of streams. Except for constructor all methods are generators.'''
    count = 0

    def __init__(self):
        self.name = str(self.__class__.__name__) + '[' + str(App.count) + ']'
        App.count = App.count + 1
        # Streams indexed by stream name, and list of clients
        self.players, self.publishers, self._clients = {}, {}, []
        if _debug:
            print(self.name, 'created')

    def __del__(self):
        if _debug:
            print(self.name, 'destroyed')

    @property
    def clients(self):
        '''everytime this property is accessed it returns a new list of clients connected to this instance.'''
        return self._clients[1:] if self._clients is not None else []

    def onConnect(self, client, *args):
        if _debug:
            print(self.name, 'onConnect', client.path)

        if "onConnect" in Event.handlers:
            Event.handlers["onConnect"](client, *args)

        return True

    def onDisconnect(self, client):
        if _debug:
            print(self.name, 'onDisconnect', client.path)

        if "onDisconnect" in Event.handlers:
            Event.handlers["onDisconnect"](client)

    def onPublish(self, client, stream):
        if _debug:
            print(self.name, 'onPublish', client.path, stream.name)

        if "onPublish" in Event.handlers:
            Event.handlers["onPublish"](client, stream)

    def onClose(self, client, stream):
        if _debug:
            print(self.name, 'onClose', client.path, stream.name)

        if "onClose" in Event.handlers:
            Event.handlers["onClose"](client, stream)

    def onPlay(self, client, stream):
        if _debug:
            print(self.name, 'onPlay', client.path, stream.name)

        if "onPlay" in Event.handlers:
            Event.handlers["onPlay"](client, stream)

    def onStop(self, client, stream):
        if _debug:
            print(self.name, 'onStop', client.path, stream.name)

        if "onStop" in Event.handlers:
            Event.handlers["onStop"](client, stream)

    def onCommand(self, client, cmd, *args):
        if _debug:
            print(self.name, 'onCommand', cmd, args)

        if "onCommand" in Event.handlers:
            Event.handlers["onCommand"](client, cmd, *args)

    def onStatus(self, client, info):
        if _debug:
            print(self.name, 'onStatus', info)

        if "onStatus" in Event.handlers:
            Event.handlers["onStatus"](client, info)

    def onResult(self, client, result):
        if _debug:
            print(self.name, 'onResult', result)

        if "onResult" in Event.handlers:
            Event.handlers["onResult"](client, result)

    def onUnpublish(self, client, cmd):
        if _debug:
            print(self.name, 'onUnpublish', cmd) 

        if "onUnpublish" in Event.handlers:
            Event.handlers["onUnpublish"](client, cmd)    
    
    def onDelete(self, client, cmd):
        if _debug:
            print(self.name, 'onDelete', cmd) 

        if "onDelete" in Event.handlers:
            Event.handlers["onDelete"](client, cmd)    

    # this is invoked every time some media packet is received from published
    # stream.
    def onPublishData(self, client, stream, message):
        if "onPublishData" in Event.handlers:
            Event.handlers["onPublishData"](client, stream, message)

        return True  # should return True so that the data is actually published in that stream

    def onPlayData(self, client, stream, message):
        if "onPlayData" in Event.handlers:
            Event.handlers["onPlayData"](client, stream, message)

        return True  # should return True so that data will be actually played in that stream

    def getfile(self, path, name, root, mode):
        if mode == 'play':
            path = getfilename(path, name, root)
            if not os.path.exists(path):
                return None
            return FLV(_debug).open(path)
        elif (mode == 'live' or mode in ('record', 'append')) and _recording:
            path = getfilename(path, name, root)
            return FLV(_debug).open(path, mode)
        return None

def getfilename(path, name, root):
    '''return the file name for the given stream. The name is derived as root/scope/name.flv where scope is
    the the path present in the path variable.'''
    if "nt" in os.name:
        if root[-1] != "\\":
            root = root + "\\"
    elif root[-1] != "/":
        root = root + "/"
    _, _, scope = path.partition('/')
    if scope:
        scope = scope + '/'
    result = root + scope + name + '.flv'
    if _debug:
        print('filename=', result)
    return result

class Event():
    """Provide a handy function to add event handle"""
    
    from inspect import signature

    handlers = {}
    __SUBSCRIBABLES = {"onConnect": len(signature(App.onConnect).parameters) - 1,
                       "onDisconnect": len(signature(App.onDisconnect).parameters) - 1, 
                       "onPublish": len(signature(App.onPublish).parameters) - 1, 
                       "onClose": len(signature(App.onClose).parameters) - 1, 
                       "onPlay": len(signature(App.onPlay).parameters) - 1, 
                       "onStop": len(signature(App.onStop).parameters) - 1, 
                       "onCommand": len(signature(App.onCommand).parameters) - 1, 
                       "onStatus": len(signature(App.onStatus).parameters) - 1, 
                       "onResult": len(signature(App.onResult).parameters) - 1, 
                       "onPublishData": len(signature(App.onPublishData).parameters) - 1, 
                       "onPlayData": len(signature(App.onPlayData).parameters) - 1,
                       "onUnpublish": len(signature(App.onUnpublish).parameters) - 1,
                       "onDelete": len(signature(App.onDelete).parameters) - 1}
    @staticmethod
    def add(event):
        """A decorator to call add_handler
        """
        def handler(*args, **kwargs):
            if len(args) > 0:
                Event.add_handler(event, args[0])
            else:
                raise ValueError("A function must be defined in this decorator.")
        return handler

    @staticmethod
    def add_handler(event, handler):
        """Bind a handler to an event
        Arguments:
            event {str} -- The name of the event
            handler {callable} -- The event handler (please note that, numbers of parameter of the handler must equal to the number of arguments passed by the respective event)

        Raises:
            TypeError: event must be a 'str'
            TypeError: handler must be a 'callable'
            ValueError: raise when argument "event" is not subscribable event
            TypeError: raise when the number of parameters of a handler does not equal to the number of arguments passed by the event
        """
        from inspect import signature

        if not isinstance(event, str):
            raise TypeError(f"event must be a 'str', not '{type(event)}'.")
        if not callable(handler):
            raise TypeError(f"handler must be a callable function, not '{type(event)}'.")
        if event not in Event.__SUBSCRIBABLES:
            raise ValueError(f"event '{event}' is not subscribable event.")

        number_of_args = len(signature(handler).parameters)
        if number_of_args != Event.__SUBSCRIBABLES[event]:
            raise TypeError(f"{event}() takes exactly {Event.__SUBSCRIBABLES[event]} argument(s) ({number_of_args} given)")

        Event.handlers[event] = handler

    @staticmethod
    def onConnect(handler):
        def handle():
            Event.add_handler("onConnect", handler)
        return handle()

    @staticmethod
    def onDisconnect(handler):
        def handle():
            Event.add_handler("onDisconnect", handler)
        return handle()

    @staticmethod
    def onPublish(handler):
        def handle():
            Event.add_handler("onPublish", handler)
        return handle()

    @staticmethod
    def onClose(handler):
        def handle():
            Event.add_handler("onClose", handler)
        return handle()

    @staticmethod
    def onPlay(handler):
        def handle():
            Event.add_handler("onPlay", handler)
        return handle()

    @staticmethod
    def onStop(handler):
        def handle():
            Event.add_handler("onStop", handler)
        return handle()

    @staticmethod
    def onCommand(handler):
        def handle():
            Event.add_handler("onCommand", handler)
        return handle()

    @staticmethod
    def onStatus(handler):
        def handle():
            Event.add_handler("onStatus", handler)
        return handle()

    @staticmethod
    def onResult(handler):
        def handle():
            Event.add_handler("onResult", handler)
        return handle()

    @staticmethod
    def onPublishData(handler):
        def handle():
            Event.add_handler("onPublishData", handler)
        return handle()

    @staticmethod
    def onPlayData(handler):
        def handle():
            Event.add_handler("onPlayData", handler)
        return handle()

    @staticmethod
    def onUnpublish(handler):
        def handle():
            Event.add_handler("onUnpublish", handler)
        return handle()

    @staticmethod
    def onDelete(handler):
        def handle():
            Event.add_handler("onDelete", handler)
        return handle()

class Wirecast(App):
    '''A wrapper around App to workaround with wirecast publisher which does not send AVC seq periodically. It defines new stream variables
    such as in publish stream 'metaData' to store first published metadata Message, and 'avcSeq' to store the last published AVC seq Message,
    and in play stream 'avcIntra' to indicate if AVC intra frame has been sent or not. These variables are created onPublish and onPlay.
    Additional, when onPlay it also also sends any published stream.metaData if found in associated publisher. When onPlayData for video, if
    it detects AVC seq it sets avcIntra so that it is not explicitly sent. This is the case with Flash Player publisher. When onPlayData for video,
    if it detects avcIntra is not set, it discards the packet until AVC NALU or seq is received. If NALU is received but previous seq is not received
    it uses the publisher's avcSeq message to send before this NALU if found.'''

    def __init__(self):
        App.__init__(self)

    def onPublish(self, client, stream):
        App.onPublish(self, client, stream)
        if not hasattr(stream, 'metaData'):
            stream.metaData = None
        if not hasattr(stream, 'avcSeq'):
            stream.avcSeq = None

    def onPlay(self, client, stream):
        App.onPlay(self, client, stream)
        if not hasattr(stream, 'avcIntra'):
            stream.avcIntra = False
        publisher = self.publishers.get(stream.name, None)
        if publisher and publisher.metaData:  # send published meta data to this player joining late
            multitask.add(stream.send(publisher.metaData.dup()))

    def onPublishData(self, client, stream, message):
        # store the first meta data on this published stream for late joining
        # players
        if message.type == Message.DATA and not stream.metaData:
            stream.metaData = message.dup()
        # H264Avc intra + seq, store it
        if message.type == Message.VIDEO and message.data[:2] == b'\x17\x00':
            stream.avcSeq = message.dup()
        return True

    def onPlayData(self, client, stream, message):
        if message.type == Message.VIDEO:  # only video packets need special handling
            # intra+seq is being sent, possibly by Flash Player publisher.
            if message.data[:2] == b'\x17\x00':
                stream.avcIntra = True
            elif not stream.avcIntra:  # intra frame hasn't been sent yet.
                # intra+nalu is being sent, possibly by wirecast publisher.
                if message.data[:2] == b'\x17\x01':
                    publisher = self.publishers.get(stream.name, None)
                    if publisher and publisher.avcSeq:  # if a publisher exists
                        def sendboth(stream, msgs):
                            stream.avcIntra = True
                            for msg in msgs:
                                yield stream.send(msg)
                        multitask.add(
                            sendboth(
                                stream, [
                                    publisher.avcSeq.dup(), message]))
                        return False  # so that caller doesn't send it again
                return False  # drop until next intra video is sent
        return True


class FlashServer(object):
    '''A RTMP server to record and stream Flash video.'''

    def __init__(self):
        '''Construct a new FlashServer. It initializes the local members.'''
        self.sock = self.server = None
        # supported applications: * means any as in {'*': App}
        self.apps = dict({'*': App, 'wirecast': Wirecast})
        # list of clients indexed by scope. First item in list is app instance.
        self.clients = dict()
        self.root = ''

    def start(self, host='0.0.0.0', port=1935):
        '''This should be used to start listening for RTMP connections on the given port, which defaults to 1935.'''
        if not self.server:
            sock = self.sock = socket.socket(type=socket.SOCK_STREAM)
            try:
                sock.bind((host, port))
            except OSError:
                if _debug:
                    print(f'port ({port}) already in use')
                exit()
            if _debug:
                print('listening on ', sock.getsockname())
            sock.listen(5)
            # start rtmp server on that socket
            server = self.server = Server(sock)
            multitask.add(self.serverlistener())

    def stop(self):
        if _debug:
            print('stopping Flash server')
        if self.server and self.sock:
            try:
                self.sock.close()
                self.sock = None
            except BaseException:
                pass
        self.server = None

    def serverlistener(self):
        '''Server listener (generator). It accepts all connections and invokes client listener'''
        try:
            while True:  # main loop to receive new connections on the server
                # receive an incoming client connection.
                client, args = (yield self.server.recv())
                # TODO: we should reject non-localhost client connections.
                if not client:                # if the server aborted abnormally,
                    break  # hence close the listener.
                if _debug:
                    print('client connection received', client, args)
                if client.objectEncoding != 0 and client.objectEncoding != 3:
                    # if client.objectEncoding != 0:
                    yield client.rejectConnection(reason='Unsupported encoding ' + str(client.objectEncoding) + '. Please use NetConnection.defaultObjectEncoding=ObjectEncoding.AMF0')
                    yield client.connectionClosed()
                else:
                    client.path = str(
                        client.agent.app) if hasattr(
                        client.agent,
                        'app') else str(
                        client.agent['app']) if isinstance(
                        client.agent,
                        dict) else None
                    if not client.path:
                        yield client.rejectConnection(reason='Missing app path')
                        break
                    name, _, scope = client.path.partition('/')
                    if '*' not in self.apps and name not in self.apps:
                        yield client.rejectConnection(reason='Application not found: ' + name)
                    else:  # create application instance as needed and add in our list
                        if _debug:
                            print(
                                'name=', name, 'name in apps', str(
                                    name in self.apps))
                        # application class
                        app = self.apps[name] if name in self.apps else self.apps['*']
                        if client.path in self.clients:
                            inst = self.clients[client.path][0]
                        else:
                            inst = app()

                        win_ack = Message()
                        win_ack.time, win_ack.type, win_ack.data = client.relativeTime, Message.WIN_ACK_SIZE, struct.pack(
                            '>L', client.writeWinSize)
                        yield client.writeMessage(win_ack)

#                        set_peer_bw = Message()
#                        set_peer_bw.time, set_peer_bw.type, set_peer_bw.data = client.relativeTime, Message.SET_PEER_BW, struct.pack('>LB', client.writeWinSize, 1)
#                        client.writeMessage(set_peer_bw)

                        try:
                            result = inst.onConnect(client, *args)
                        except BaseException:
                            if _debug:
                                print(sys.exc_info())
                            yield client.rejectConnection(reason='Exception on onConnect')
                            continue
                        if result is True or result is None:
                            if client.path not in self.clients:
                                self.clients[client.path] = [inst]
                                inst._clients = self.clients[client.path]
                            self.clients[client.path].append(client)
                            if result is True:
                                yield client.accept()  # TODO: else how to kill this task when rejectConnection() later
                            # receive messages from client.
                            multitask.add(self.clientlistener(client))
                        else:
                            yield client.rejectConnection(reason='Rejected in onConnect')
        except GeneratorExit:
            pass  # terminate
        except BaseException:
            if _debug:
                print('serverlistener exception', traceback.print_exc())

    def clientlistener(self, client):
        '''Client listener (generator). It receives a command and invokes client handler, or receives a new stream and invokes streamlistener.'''
        try:
            while True:
                # receive new message from client
                msg, arg = (yield client.recv())
                if not msg:                   # if the client disconnected,
                    if _debug:
                        print('connection closed from client')
                    break  # come out of listening loop.
                if msg == 'command':          # handle a new command
                    multitask.add(self.clienthandler(client, arg))
                # a new stream is created, handle the stream.
                elif msg == 'stream':
                    arg.client = client
                    multitask.add(self.streamlistener(arg))
        except BaseException:
            if _debug:
                print(
                    'clientlistener exception',
                    (sys and sys.exc_info() or None))

        try:
            # client is disconnected, clear our state for application instance.
            if _debug:
                print('cleaning up client', client.path)
            inst = None
            if client.path in self.clients:
                inst = self.clients[client.path][0]
                self.clients[client.path].remove(client)
            for stream in list(client.streams.values()):  # for all streams of this client
                self.closehandler(stream)
            client.streams.clear()  # and clear the collection of streams
            # no more clients left, delete the instance.
            if client.path in self.clients and len(
                    self.clients[client.path]) == 1:
                if _debug:
                    print('removing the application instance')
                inst = self.clients[client.path][0]
                inst._clients = None
                del self.clients[client.path]
            if inst is not None:
                inst.onDisconnect(client)
        except BaseException:
            if _debug:
                print(
                    'clientlistener exception',
                    (sys and sys.exc_info() or None))

    def closehandler(self, stream):
        '''A stream is closed explicitly when a closeStream command is received from given client.'''
        if stream.client is not None:
            inst = self.clients[stream.client.path][0]
            # clear the published stream
            if stream.name in inst.publishers and inst.publishers[stream.name] == stream:
                inst.onClose(stream.client, stream)
                del inst.publishers[stream.name]
            if stream.name in inst.players and stream in inst.players[stream.name]:
                inst.onStop(stream.client, stream)
                inst.players[stream.name].remove(stream)
                if len(inst.players[stream.name]) == 0:
                    del inst.players[stream.name]
            stream.close()

    def clienthandler(self, client, cmd):
        '''A generator to handle a single command on the client.'''
        inst = self.clients[client.path][0]
        if inst:
            if cmd.name == '_error':
                if hasattr(inst, 'onStatus'):
                    result = inst.onStatus(client, cmd.args[0])
            elif cmd.name == '_result':
                if hasattr(inst, 'onResult'):
                    result = inst.onResult(client, cmd.args[0])
            elif cmd.name == 'FCUnpublish':
                try:
                    self.unpublishhandler(client, cmd)
                except:
                    pass
                if hasattr(inst, 'onUnpublish'):
                    result = inst.onUnpublish(client, cmd.args[0])
            elif cmd.name == 'deleteStream':
                try:
                    self.deletehandler(client, cmd)
                except:
                    pass
                if hasattr(inst, 'onDelete'):
                    result = inst.onDelete(client, cmd.args[0])
            else:
                res, code, result = Command(), '_result', None
                try:
                    result = inst.onCommand(client, cmd.name, *cmd.args)
                except BaseException:
                    if _debug:
                        print(
                            'Client.call exception',
                            (sys and sys.exc_info() or None))
                    code = '_error'
                args = (result,) if result is not None else dict()
                res.id, res.time, res.name, res.type = cmd.id, client.relativeTime, code, client.rpc
                res.args, res.cmdData = args, None
                if _debug:
                    print(
                        'Client.call method=',
                        code,
                        'args=',
                        args,
                        ' msg=',
                        res.toMessage())
                yield client.writeMessage(res.toMessage())
        yield

    def streamlistener(self, stream):
        '''Stream listener (generator). It receives stream message and invokes streamhandler.'''
        try:
            stream.recordfile = None  # so that it doesn't complain about missing attribute
            while True:
                msg = (yield stream.recv())
                if not msg:
                    if _debug:
                        print('stream closed')
                    self.closehandler(stream)
                    break
                # if _debug: msg
                multitask.add(self.streamhandler(stream, msg))
        except BaseException:
            if _debug:
                print(
                    'streamlistener exception',
                    (sys and sys.exc_info() or None))

    def streamhandler(self, stream, message):
        '''A generator to handle a single message on the stream.'''
        try:
            if message.type == Message.RPC or message.type == Message.RPC3:
                cmd = Command.fromMessage(message)
                if _debug:
                    print('streamhandler received cmd=', cmd)
                if cmd.name == 'publish':
                    yield self.publishhandler(stream, cmd)
                elif cmd.name == 'play':
                    yield self.playhandler(stream, cmd)
                elif cmd.name == 'closeStream':
                    self.closehandler(stream)
                elif cmd.name == 'seek':
                    yield self.seekhandler(stream, cmd)
            else:  # audio or video message
                yield self.mediahandler(stream, message)
        except GeneratorExit:
            pass
        except BaseException:
            if _debug:
                print('exception in streamhandler', (sys and sys.exc_info()))

    def publishhandler(self, stream, cmd):
        '''A new stream is published. Store the information in the application instance.'''
        try:
            stream.mode = 'live' if len(
                cmd.args) < 2 else cmd.args[1]  # live, record, append
            stream.name = cmd.args[0]
            if _debug:
                print('publishing stream=', stream.name, 'mode=', stream.mode)
            if stream.name and '?' in stream.name:
                stream.name = stream.name.partition('?')[0]
            inst = self.clients[stream.client.path][0]
            if (stream.name in inst.publishers):
                raise ValueError('Stream name already in use')
            # store the client for publisher
            inst.publishers[stream.name] = stream
            inst.onPublish(stream.client, stream)
            stream.recordfile = inst.getfile(
                stream.client.path, stream.name, self.root, stream.mode)
            response = Command(
                name='onStatus',
                id=cmd.id,
                tm=stream.client.relativeTime,
                args=[
                    amf.Object(
                        level='status',
                        code='NetStream.Publish.Start',
                        description='',
                        details=None)])
            yield stream.send(response)
        except ValueError as e:  # some error occurred. inform the app.
            if _debug:
                print('error in publishing stream', str(e))
            response = Command(
                name='onStatus',
                id=cmd.id,
                tm=stream.client.relativeTime,
                args=[
                    amf.Object(
                        level='error',
                        code='NetStream.Publish.BadName',
                        description=str(e),
                        details=None)])
            yield stream.send(response)

    def playhandler(self, stream, cmd):
        '''A new stream is being played. Just updated the players list with this stream.'''
        try:
            inst = self.clients[stream.client.path][0]
            name = stream.name = cmd.args[0]  # store the stream's name
            if stream.name and '?' in stream.name:
                name = stream.name = stream.name.partition('?')[0]
            start = cmd.args[1] if len(cmd.args) >= 2 else -2
            if name not in inst.players:
                # initialize the players for this stream name
                inst.players[name] = []
            # store the stream as players of this name
            if stream not in inst.players[name]:
                inst.players[name].append(stream)
            task = None
            if start >= 0 or start == -2 and name not in inst.publishers:
                stream.playfile = inst.getfile(
                    stream.client.path, stream.name, self.root, 'play')
                if stream.playfile:
                    if start > 0:
                        stream.playfile.seek(start)
                    task = stream.playfile.reader(stream)
                elif start >= 0:
                    raise ValueError('Stream name not found')
            if _debug:
                print('playing stream=', name, 'start=', start)
            inst.onPlay(stream.client, stream)

            # Default chunk size is 128. It is pretty small when we stream high audio and video quality.
            # So, send the choosen chunk size to flash client.
            stream.client.writeChunkSize = Protocol.HIGH_WRITE_CHUNK_SIZE
            m0 = Message()  # SetChunkSize
            m0.time, m0.type, m0.data = stream.client.relativeTime, Message.CHUNK_SIZE, struct.pack(
                '>L', stream.client.writeChunkSize)
            yield stream.client.writeMessage(m0)

#            m1 = Message() # UserControl/StreamIsRecorded
#            m1.time, m1.type, m1.data = stream.client.relativeTime, Message.USER_CONTROL, struct.pack('>HI', 4, stream.id)
#            yield stream.client.writeMessage(m1)

            m2 = Message()  # UserControl/StreamBegin
            m2.time, m2.type, m2.data = stream.client.relativeTime, Message.USER_CONTROL, struct.pack(
                '>HI', 0, stream.id)
            yield stream.client.writeMessage(m2)

            response = Command(name='onStatus', id=cmd.id, args=[amf.Object(level='status',code='NetStream.Play.Reset', description=stream.name, details=None)])
            yield stream.send(response)

            response = Command(
                name='onStatus',
                id=cmd.id,
                tm=stream.client.relativeTime,
                args=[
                    amf.Object(
                        level='status',
                        code='NetStream.Play.Start',
                        description=stream.name,
                        details=None)])
            yield stream.send(response)

            response = Command(name='onStatus', id=cmd.id, tm=stream.client.relativeTime, args=[amf.Object(level='status',code='NetStream.Play.PublishNotify', description=stream.name, details=None)])
            yield stream.send(response)

            if task is not None:
                multitask.add(task)
        except ValueError as e:  # some error occurred. inform the app.
            if _debug:
                print('error in playing stream', str(e))
            response = Command(
                name='onStatus',
                id=cmd.id,
                tm=stream.client.relativeTime,
                args=[
                    amf.Object(
                        level='error',
                        code='NetStream.Play.StreamNotFound',
                        description=str(e),
                        details=None)])
            yield stream.send(response)

    def seekhandler(self, stream, cmd):
        '''A stream is seeked to a new position. This is allowed only for play from a file.'''
        try:
            offset = cmd.args[0]
            if stream.playfile is None or stream.playfile.type != 'read':
                raise ValueError('Stream is not seekable')
            stream.playfile.seek(offset)
            response = Command(
                name='onStatus',
                id=cmd.id,
                tm=stream.client.relativeTime,
                args=[
                    amf.Object(
                        level='status',
                        code='NetStream.Seek.Notify',
                        description=stream.name,
                        details=None)])
            yield stream.send(response)
        except ValueError as e:  # some error occurred. inform the app.
            if _debug:
                print('error in seeking stream', str(e))
            response = Command(
                name='onStatus',
                id=cmd.id,
                tm=stream.client.relativeTime,
                args=[
                    amf.Object(
                        level='error',
                        code='NetStream.Seek.Failed',
                        description=str(e),
                        details=None)])
            yield stream.send(response)

    def mediahandler(self, stream, message):
        '''Handle incoming media on the stream, by sending to other stream in this application instance.'''
        if stream.client is not None:
            inst = self.clients[stream.client.path][0]
            result = inst.onPublishData(stream.client, stream, message)

            if result:
                for s in (inst.players.get(stream.name, [])):
                    # if _debug: print 'D', stream.name, s.name
                    m = message.dup()
                    result = inst.onPlayData(s.client, s, m)
                    if result:
                        yield s.send(m)
                if stream.recordfile is not None:
                    stream.recordfile.write(message)

    def unpublishhandler(self, client, cmd):
        raise NotImplementedError()

    def deletehandler(self, client, cmd):
        raise NotImplementedError()

# The main routine to start, run and stop the service
if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser(version=f'{_version}, {_build}')
    parser.add_option(
        '-i',
        '--host',
        dest='host',
        default='0.0.0.0',
        help="listening IP address. Default '0.0.0.0'")
    parser.add_option(
        '-p',
        '--port',
        dest='port',
        default=1935,
        type="int",
        help='listening port number. Default 1935')
    parser.add_option(
        '-r',
        '--root',
        dest='root',
        default='./',
        help="document path prefix. Directory must end with /. Default './'")
    parser.add_option(
        '-d',
        '--debug',
        dest='debug',
        default=False,
        action='store_true',
        help='enable debug trace')
    parser.add_option(
        '-v',
        '--verbose',
        dest='verbose',
        default=False,
        action='store_true',
        help='enable verbose mode (display all traffic)')
    parser.add_option(
        '-k',
        '--recording',
        dest='recording',
        default=False,
        action='store_true',
        help='keep live as a video')
    (options, args) = parser.parse_args()

    _verbose = options.verbose
    _recording = options.recording
    
    if _verbose:
        _debug = True
    else:
        _debug = options.debug
    try:
        agent = FlashServer()
        agent.root = options.root
        agent.start(options.host, options.port)
        print(time.asctime(), f'RTMPLite Server Starts - {options.host}:{options.port} {_version}')
        multitask.run()
    except KeyboardInterrupt:
        agent.stop()
    
    print(time.asctime(), 'RTMPLite Server Stops')
