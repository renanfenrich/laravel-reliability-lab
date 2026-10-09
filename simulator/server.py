import hashlib, json, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path == '/live' else 404); self.end_headers()
    def do_POST(self):
        try:
            if self.path != '/process': raise ValueError()
            data=json.loads(self.rfile.read(min(int(self.headers.get('Content-Length',0)),4096)))
            payload=data['payload']; delay=int(payload['latency_ms']); fail=int(payload['fail_attempts'])
            if not 0<=delay<=4000 or not 0<=fail<=3: raise ValueError()
            time.sleep(delay/1000)
            status=503 if int(data['attempt'])<=fail else 200
            result={'error':'synthetic dependency failure'} if status==503 else {'checksum':hashlib.sha256(payload['subject'].encode()).hexdigest()}
            self.send_response(status); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(json.dumps(result).encode())
            print(json.dumps({'event':'simulator.response','request_id':self.headers.get('X-Request-ID'),'report_id':data['report_id'],'status':status,'latency_ms':delay}),flush=True)
        except (ValueError,KeyError,TypeError): self.send_response(422); self.end_headers()
    def log_message(self,*args): pass
ThreadingHTTPServer(('0.0.0.0',8081),Handler).serve_forever()
