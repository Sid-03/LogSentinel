import re
import json
import csv
from datetime import datetime

class BaseLogParser:
    name = "base"
    multiline = False
    def match(self, line):
        raise NotImplementedError

    def normalize(self, match_dict, filename):
        # Always return {timestamp, level, message, source}
        d = dict(match_dict)
        d['source'] = filename
        return d

# 1. Apache/Nginx Logs (Common Log Format)
class ApacheLogParser(BaseLogParser):
    name = "apache"
    regex = re.compile(r'^(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<request>[^"]+)" (?P<status>\d{3}) (?P<size>\d+)')
    def match(self, line):
        m = self.regex.match(line)
        if m:
            dt = datetime.strptime(m.group('timestamp'), "%d/%b/%Y:%H:%M:%S %z")
            return {
                'timestamp': dt.isoformat(),
                'level': 'INFO',
                'message': f"{m.group('request')} (status {m.group('status')}, size {m.group('size')})"
            }
        return None

# 2. JSON Logs
class JSONLogParser(BaseLogParser):
    name = "json"
    def match(self, line):
        try:
            obj = json.loads(line)
            if all(k in obj for k in ("timestamp", "level", "message")):
                return {
                    'timestamp': obj['timestamp'],
                    'level': obj['level'],
                    'message': obj['message']
                }
        except Exception:
            return None
        return None

# 3. Syslog Logs (Linux)
class SyslogParser(BaseLogParser):
    name = "syslog"
    regex = re.compile(r'^(?P<timestamp>[A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2}) (?P<host>\S+) (?P<process>[\w\-\[\].]+): (?P<message>.*)')
    def match(self, line):
        m = self.regex.match(line)
        if m:
            # Guess year as current year
            dt = datetime.strptime(f"{datetime.now().year} {m.group('timestamp')}", "%Y %b %d %H:%M:%S")
            return {
                'timestamp': dt.isoformat(),
                'level': 'INFO',
                'message': m.group('message')
            }
        return None

# 4. Java Exception / Stacktrace Logs (multiline)
class JavaStacktraceParser(BaseLogParser):
    name = "java_stacktrace"
    multiline = True
    def match(self, lines):
        if not lines[0].startswith('java.') and not lines[0].startswith('Exception'):
            return None
        msg = '\n'.join(lines)
        return {
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': msg
        }

# 5. Custom Application Logs
class CustomAppLogParser(BaseLogParser):
    name = "custom_app"
    regex = re.compile(r'^\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(?P<level>\w+)\] \[(?P<module>[^\]]+)\] - (?P<message>.*)')
    def match(self, line):
        m = self.regex.match(line)
        if m:
            return {
                'timestamp': m.group('timestamp'),
                'level': m.group('level'),
                'message': f"[{m.group('module')}] {m.group('message')}"
            }
        return None

# 6. CSV-Formatted Logs
class CSVLogParser(BaseLogParser):
    name = "csv"
    def __init__(self):
        self.header = None
    def match(self, line):
        # Only match if header is present
        if self.header is not None:
            reader = csv.DictReader([line], fieldnames=self.header)
            row = next(reader)
            if 'timestamp' in row and 'level' in row and 'message' in row:
                return {
                    'timestamp': row['timestamp'],
                    'level': row['level'],
                    'message': row['message']
                }
        elif ',' in line and all(h in line for h in ['timestamp','level','message']):
            self.header = [h.strip() for h in line.split(',')]
        return None

# 7. Windows Event Logs (block)
class WindowsEventLogParser(BaseLogParser):
    name = "windows_event"
    multiline = True
    def match(self, lines):
        if not lines[0].startswith('Date:'):
            return None
        date, source, eventid, desc = None, None, None, []
        for line in lines:
            if line.startswith('Date:'):
                date = line.split('Date:')[1].strip()
            elif line.startswith('Source:'):
                source = line.split('Source:')[1].strip()
            elif line.startswith('Event ID:'):
                eventid = line.split('Event ID:')[1].strip()
            elif line.startswith('Description:'):
                desc.append(line.split('Description:')[1].strip())
            else:
                desc.append(line.strip())
        if date and source and eventid:
            return {
                'timestamp': date,
                'level': 'INFO',
                'message': f"{source} (Event ID: {eventid}) - {' '.join(desc)}"
            }
        return None

# 8. Kubernetes/Docker Logs
class K8sDockerLogParser(BaseLogParser):
    name = "k8s_docker"
    regex = re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z) (?P<stream>\w+) (?P<flag>\w) (?P<message>.*)')
    def match(self, line):
        m = self.regex.match(line)
        if m:
            return {
                'timestamp': m.group('timestamp'),
                'level': m.group('stream').upper(),
                'message': m.group('message')
            }
        return None

# 9. Multiline Logs (e.g., Python Tracebacks)
class PythonTracebackParser(BaseLogParser):
    name = "python_traceback"
    multiline = True
    def match(self, lines):
        if not (lines[0].startswith('[') and 'ERROR' in lines[0]):
            return None
        msg = '\n'.join(lines)
        ts = re.findall(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', lines[0])
        timestamp = ts[0] if ts else datetime.now().isoformat()
        return {
            'timestamp': timestamp,
            'level': 'ERROR',
            'message': msg
        }

# 10. Delimited Logs (|, tab)
class DelimitedLogParser(BaseLogParser):
    name = "delimited"
    regex = re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})[|\t](?P<level>\w+)[|\t](?P<message>.+)')
    def match(self, line):
        m = self.regex.match(line)
        if m:
            return {
                'timestamp': m.group('timestamp'),
                'level': m.group('level'),
                'message': m.group('message')
            }
        return None

# 0. Simple YYYY-MM-DD HH:MM:SS LEVEL Message
class SimpleLogParser(BaseLogParser):
    name = "simple"
    regex = re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>\w+) (?P<message>.+)$')
    def match(self, line):
        m = self.regex.match(line)
        if m:
            return {
                'timestamp': m.group('timestamp'),
                'level': m.group('level'),
                'message': m.group('message'),
            }
        return None

# List of all parser classes (priority order)
ALL_PARSERS = [
    SimpleLogParser(),
    ApacheLogParser(),
    JSONLogParser(),
    SyslogParser(),
    JavaStacktraceParser(),
    CustomAppLogParser(),
    CSVLogParser(),
    WindowsEventLogParser(),
    K8sDockerLogParser(),
    PythonTracebackParser(),
    DelimitedLogParser(),
]
