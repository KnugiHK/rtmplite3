import struct
try:
    from rtmplite3 import amf # try import from package
except:
    try:
        import amf
    except:
        exit("Required module not found")
def truncate(data, max=100):
    data1 = data and len(data) > max and data[:max]
    if isinstance(data1, str):
        data2 = f'...({len(data)})' or data
    elif isinstance(data1, bytes):
        data2 = b'...(%d)' % len(data) or data
    else:
        data1 = str(data1)
        data2 = f'...({len(data)})' or data
    return str(data1 + data2)


class Header(object):
    # Chunk type 0 = FULL
    # Chunk type 1 = MESSAGE
    # Chunk type 2 = TIME
    # Chunk type 3 = SEPARATOR
    FULL, MESSAGE, TIME, SEPARATOR, MASK = 0x00, 0x40, 0x80, 0xC0, 0xC0

    def __init__(self, channel=0, time=0, size=None, type=None, streamId=0):

        self.channel = channel   # in fact, this will be the fmt + cs id
        self.time = time         # timestamp[delta]
        self.size = size         # message length
        self.type = type         # message type id
        self.streamId = streamId  # message stream id

        if (channel < 64):
            self.hdrdata = struct.pack('>B', channel)
        elif (channel < 320):
            self.hdrdata = b'\x00' + struct.pack('>B', channel - 64)
        else:
            self.hdrdata = b'\x01' + struct.pack('>H', channel - 64)

    def toBytes(self, control):
        data = (self.hdrdata[0] | control).to_bytes(1, 'big')
        if len(self.hdrdata) >= 2:
            data += self.hdrdata[1:]

        # if the chunk type is not 3
        if control != Header.SEPARATOR:
            data += struct.pack('>I', self.time if self.time <
                                0xFFFFFF else 0xFFFFFF)[1:]  # add time in 3 bytes
            # if the chunk type is not 2
            if control != Header.TIME:
                data += struct.pack('>I', self.size)[1:]  # add size in 3 bytes
                data += struct.pack('>B', self.type)  # add type in 1 byte
                # if the chunk type is not 1
                if control != Header.MESSAGE:
                    # add streamId in little-endian 4 bytes
                    data += struct.pack('<I', self.streamId)
            # add the extended time part to the header if timestamp[delta] >=
            # 16777215
            if self.time >= 0xFFFFFF:
                data += struct.pack('>I', self.time)
        return data

    def __repr__(self):
        return (
            f"<Header channel={self.channel} time={self.time} size={self.size} type={Message.type_name.get(self.type,'unknown')} ({self.type}) streamId={self.streamId}>")

    def dup(self):
        return Header(
            channel=self.channel,
            time=self.time,
            size=self.size,
            type=self.type,
            streamId=self.streamId)


class Message(object):
    # message types: RPC3, DATA3,and SHAREDOBJECT3 are used with AMF3
    CHUNK_SIZE, ABORT, ACK, USER_CONTROL, WIN_ACK_SIZE, SET_PEER_BW, AUDIO, VIDEO, DATA3, SHAREDOBJ3, RPC3, DATA, SHAREDOBJ, RPC, AGGREGATE = \
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x08, 0x09, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x16
    type_name = dict(
        enumerate(
            'unknown chunk-size abort ack user-control win-ack-size set-peer-bw unknown audio video unknown unknown unknown unknown unknown data3 sharedobj3 rpc3 data sharedobj rpc unknown aggregate'.split()))

    def __init__(self, hdr=None, data=''):
        self.header, self.data = hdr or Header(), data

    # define properties type, streamId and time to access
    # self.header.(property)  
    def _gtype(self):
        return self.header.type
        
    def _stype(self, type):
        self.header.type = type
    
    type = property(fget=_gtype, fset=_stype)
    
    def _gstreamId(self):
        return self.header.streamId
        
    def _sstreamId(self, streamId):
        self.header.streamId = streamId
    
    streamId = property(fget=_gstreamId, fset=_sstreamId)
    
    def _gtime(self):
        return self.header.time
        
    def _stime(self, time):
        self.header.time = time
    
    time = property(fget=_gtime, fset=_stime) 

    @property
    def size(self): return len(self.data)

    def __repr__(self):
        return (f"<Message header={self.header} data={truncate(self.data)}>")

    def dup(self):
        return Message(self.header.dup(), self.data[:])


class Command(object):
    ''' Class for command / data messages'''

    def __init__(
            self,
            type=Message.RPC,
            name=None,
            id=None,
            tm=0,
            cmdData=None,
            args=[]):
        '''Create a new command with given type, name, id, cmdData and args list.'''
        self.type, self.name, self.id, self.time, self.cmdData, self.args = type, name, id, tm, cmdData, args[:]

    def __repr__(self):
        return (f"<Command type={self.type} name={self.name} id={self.id} data={self.cmdData} args={self.args}>")

    def setArg(self, arg):
        self.args.append(arg)

    def getArg(self, index):
        return self.args[index]

    @classmethod
    def fromMessage(cls, message):
        ''' initialize from a parsed RTMP message'''
        assert (
            message.type in [
                Message.RPC,
                Message.RPC3,
                Message.DATA,
                Message.DATA3])

        length = len(message.data)
        if length == 0:
            raise ValueError('zero length message data')

        if message.type == Message.RPC3 or message.type == Message.DATA3:
            assert message.data[0] == b'\x00'  # must be 0 in AMF3
            data = message.data[1:]
        else:
            data = message.data

        #from pyamf import remoting
        amfReader = amf.AMF0(data)
        inst = cls()
        inst.type = message.type
        inst.time = message.time
        inst.name = amfReader.read()  # first field is command name

        try:
            if message.type == Message.RPC or message.type == Message.RPC3:
                inst.id = amfReader.read()  # second field *may* be message id
                inst.cmdData = amfReader.read()  # third is command data
            else:
                inst.id = 0
            inst.args = []  # others are optional
            while True:
                inst.args.append(amfReader.read())  # amfReader.read())
        except EOFError:
            pass
        return inst

    def toMessage(self):
        msg = Message()
        assert self.type
        msg.type = self.type
        msg.time = self.time
        output = amf.AMFBytesIO()
        amfWriter = amf.AMF0(output)
        amfWriter.write(self.name)
        if msg.type == Message.RPC or msg.type == Message.RPC3:
            amfWriter.write(self.id)
            amfWriter.write(self.cmdData)
        for arg in self.args:
            amfWriter.write(arg)
        output.seek(0)
        # hexdump.hexdump(output)
        # output.seek(0)
        if msg.type == Message.RPC3 or msg.type == Message.DATA3:
            data = b'\x00' + output.read()
        else:
            data = output.read()
        msg.data = data
        output.close()
        return msg