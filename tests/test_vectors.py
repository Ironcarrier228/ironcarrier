import sys
import os
import socket
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__), '..'))

from ironcarrier.core.stats import StatsCollector
from ironcarrier.vectors.layer4.udp_flood import Attack as UDPFlood
from ironcarrier.vectors.layer4.syn_flood import Attack as SYNFlood
from ironcarrier.vectors.layer7.http_flood import Attack as HTTPFlood
from ironcarrier.vectors.layer7.slowloris import Attack as Slowloris


class TestStats:
    def test_add_packets(self):
        stats = StatsCollector()
        stats.add_packets(100, 64000)
        assert stats.packets.get() == 100
        assert stats.bytes_sent.get() == 64000
    
    def test_errors(self):
        stats = StatsCollector()
        for _ in range(5):
            stats.add_error()
        assert stats.errors.get() == 5
    
    def test_reset(self):
        stats = StatsCollector()
        stats.add_packets(50, 32000)
        stats.reset()
        assert stats.packets.get() == 0


class TestPacketConstruction:
    def test_udp_packet_size(self):
        attack = UDPFlood('127.0.0.1', 1234, 10, threads=1, stats=StatsCollector(), size=512)
        assert attack.packet_size == 512
    
    def test_syn_packet_size(self):
        attack = SYNFlood('127.0.0.1', 1234, 10, threads=1, stats=StatsCollector())
        # SYN packet = 40 bytes (20 IP + 20 TCP)
        assert attack._build_packet().__len__() == 40


class TestConfig:
    def test_default_config(self):
        from ironcarrier.core.config import Config
        config = Config()
        assert config.get('general.name') == 'IronCarrier'
        assert config.get('engine.max_threads') == 500
        assert config.get('vectors.tcp.flags') == ['SYN', 'ACK', 'PSH+ACK', 'RST']
    
    def test_env_override(self):
        os.environ['IRONCARRIER_ENGINE_MAX_THREADS'] = '1000'
        config = Config()
        assert config.get('engine.max_threads') == 1000
    
    def _set_and_get(self):
        config = Config()
        config.set('vectors.udp.size', 2048)
        assert config.get('vectors.udp.size') == 2048
    
    def test_load_missing_file(self):
        try:
            Config('/nonexistent.yaml')
            assert False
        except FileNotFoundError:
            assert True
    
    def test_json_config(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            f.write('{"ironcarrier": {"general": {"name": "Test"}}')
        
        config = Config(f.name)
        assert config.get('general.name') == 'Test'
    
    def test_yaml_config(self):
        import tempfile
        try:
            import yaml
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
                f.write('ironcarrier:\n  general:\n    name: "Test"\n')
            
            config = Config(f.name)
            assert config.get('general.name') == 'Test'
        except ImportError:
            pass


def test_all():
    print("[*] Running tests...\n")
    
    print("  [1/3] Stats...")
    test = TestStats()
    test.test_add_packets()
    test.test_errors()
    test.test_reset()
    print("         ✓ Stats OK")
    
    print("  [2/3] Packets...")
    test = TestPacketConstruction()
    test.test_udp_packet_size()
    test.test_syn_packet_size()
    print("         ✓ Packets OK")
    
    print("  [3/3] Config...")
    test = TestConfig()
    test.test_default_config()
    test.test_env_override()
    test._set_and_get()
    test.test_load_missing_file()
    test.test_json_config()
    test.test_yaml_config()
    print("         ✓ Config OK")
    
    print("\n[+] All tests passed!")
    return 0


if __name__ == '__main__':
    sys.exit(test_all())
