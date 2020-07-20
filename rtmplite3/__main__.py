from .rtmp import _version, _build, FlashServer
from . import multitask
import time
from optparse import OptionParser
def main():
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
main()