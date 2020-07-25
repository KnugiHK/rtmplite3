import struct
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
    for p in ['type', 'streamId', 'time']:
        exec(f'def _g{p}(self): return self.header.{p}')
        exec(f'def _s{p}(self, {p}): self.header.{p} = {p}')
        exec(f'{p} = property(fget=_g{p}, fset=_s{p})')

    @property
    def size(self): return len(self.data)

    def __repr__(self):
        return (f"<Message header={self.header} data={truncate(self.data)}>")

    def dup(self):
        return Message(self.header.dup(), self.data[:])