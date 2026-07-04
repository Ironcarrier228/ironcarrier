#!/usr/bin/env python3
"""
WebSocket Handler
Real-time updates via WebSocket
"""

import json
import threading
import time
from collections import deque
from flask import Blueprint, request, Response
from typing import Optional

try:
    from geventwebsocket.handler import WebSocketHandler
    from gevent.pywsgi import WSGIServer
    HAS_GEVENT = True
except ImportError:
    HAS_GEVENT = False

try:
    import websocket
    HAS_WEBSOCKET_CLIENT = True
except ImportError:
    HAS_WEBSOCKET_CLIENT = False


def WebSocketBlueprint(c2_server=None):
    """Create WebSocket blueprint"""
    bp = Blueprint('ws', __name__)
    bp._c2 = c2_server
    bp._clients = set()
    bp._message_queue = deque(maxlen=1000)
    bp._lock = threading.Lock()
    
    def broadcast_event(event_type: str, data: dict):
        """Queue event for broadcast"""
        msg = json.dumps({'type': event_type, 'data': data, 'ts': time.time()})
        with bp._lock:
            bp._message_queue.append(msg)
    
    # Register callbacks on C2 server
    if c2_server:
        def on_connect(agent):
            broadcast_event('agent_connect', agent.to_dict())
        
        def on_disconnect(agent):
            broadcast_event('agent_disconnect', {'agent_id': agent.info.agent_id})
        
        def on_message(agent, message):
            from ironcarrier.c2.protocol import MessageType
            msg_dict = message.to_dict()
            msg_dict['agent_id'] = agent.info.agent_id
            broadcast_event('message', msg_dict)
        
        def on_attack_update(job):
            broadcast_event('attack_update', {
                'job_id': job.job_id,
                'status': job.status,
                'vector': job.vector,
                'target': job.target,
            })
        
        c2_server.on_agent_connect(on_connect)
        c2_server.on_agent_disconnect(on_disconnect)
        c2_server.on_message(on_message)
        c2_server.on_attack_update(on_attack_update)
    
    @bp.route('/stream')
    def stream():
        """SSE (Server-Sent Events) stream - fallback for no WebSocket"""
        def generate():
            while True:
                with bp._lock:
                    while bp._message_queue:
                        msg = bp._message_queue.popleft()
                        yield f"data: {msg}\n\n"
                time.sleep(0.5)
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )
    
    @bp.route('/connect')
    def ws_connect():
        """WebSocket connection endpoint"""
        if not request.environ.get('wsgi.websocket'):
            return {'error': 'WebSocket required'}, 400
        
        ws = request.environ['wsgi.websocket']
        
        with bp._lock:
            bp._clients.add(ws)
        
        try:
            while True:
                # Send queued messages
                with bp._lock:
                    while bp._message_queue:
                        msg = bp._message_queue.popleft()
                        try:
                            ws.send(msg)
                        except Exception:
                            return
                time.sleep(0.1)
        except Exception:
            pass
        finally:
            with bp._lock:
                bp._clients.discard(ws)
    
    # Store broadcast function on blueprint for external use
    bp.broadcast = broadcast_event
    
    return bp
