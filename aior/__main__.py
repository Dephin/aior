import os
import sys

if __package__ == '':
    path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, path)


def _main():
    if len(sys.argv) > 2:
        cmd, opt = sys.argv[1:]
        if cmd == "run":
            if opt == "http":
                from aior.examples.simple_http import main as run_simple_http_server
                run_simple_http_server()
            elif opt == "inbound":
                from aior.examples.simple_inbound import main as run_simple_inbound_server
                run_simple_inbound_server()
            elif opt == "outbound":
                from aior.examples.simple_outbound import main as run_simple_outbound_client
                run_simple_outbound_client()
            else:
                raise ValueError
        else:
            raise ValueError
    else:
        raise SyntaxError


if __name__ == '__main__':
    sys.exit(_main())
