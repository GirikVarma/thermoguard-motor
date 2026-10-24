"""Serve the offline ThermoGuard application. Runtime: Python standard library only."""
from __future__ import annotations
import argparse
import functools
import socket
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parent

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
    def log_message(self,format,*args):
        if args and str(args[0]).startswith('GET'): return
        super().log_message(format,*args)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    handler=functools.partial(Handler,directory=str(ROOT/'web'))
    for port in range(args.port,args.port+10):
        try:server=ThreadingHTTPServer(('127.0.0.1',port),handler);break
        except PermissionError:
            raise SystemExit('The operating system blocked local network binding. Open ThermoGuard_Standalone.html instead.')
        except OSError:continue
    else:raise SystemExit('No local port available. Try --port 9000.')
    url=f'http://127.0.0.1:{port}'
    print(f'ThermoGuard Motor is running at {url}',flush=True)
    print('Inference runs locally in your browser. Press Ctrl+C to stop.',flush=True)
    if not args.no_browser:threading.Timer(.8,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
