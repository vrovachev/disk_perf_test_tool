import os.path
import re

import texttable


from ..itest import TwoScriptTest
from ..itest import TestResults


class OmgTestResults(TestResults):

    def __init__(self, config, results, raw_result, run_interval):
        super(OmgTestResults, self).__init__(config, results, raw_result,
                                             run_interval)
        self.parse()

    def parse(self):
        durations = []
        received = 0
        latencys = []

        latency_mins = []
        latency_maxs = []
        sent = self.config.params['run_opts']['num_messages'] \
               * self.config.params['run_opts']['clients']

        parts = self.raw_result.strip().split("==== wally ====")
        servers_log = parts[2:]

        for server_log in servers_log:
            results = re.findall(
                    'duration: (\\d+\\.\\d+) count: (\\d+)(.*)latency: '
                    '([-+]?\\d+\\.\\d+) min: ([-+]?\\d+\\.\\d+) max: ([-+]?\\d+\\.\\d+)',
                    server_log)
            if results:
                duration, count, _x, latency, latency_max, latency_min = \
                    results[0]
            else:
                duration, count, latency, latency_max, latency_min = 0,0,0,0, 0

            # 5 seconds server do not receive messages
            durations.append(float(duration) - 5)
            received += int(count)
            latencys.append(float(latency))
            latency_mins.append(float(latency_min))
            latency_maxs.append(float(latency_max))

        duration = max(durations)
        totalms = int(received / duration)
        sucess = int((received / sent) * 100)
        latency = sum(latencys) / len(latencys)
        latency_min = min(latency_mins)
        latency_max = max(latency_maxs)
        self.results = dict()
        self.results['sent'] = float(sent)
        self.results['duration'] = int(duration)
        self.results['received'] = received
        self.results['bandwidth'] = self.results['duration'] and \
            self.results['received'] / self.results['duration']
        self.results['success'] = self.results['received'] and \
            int(self.results['sent'] / self.results['received'] * 100)
        self.results['latency'] = latency
        self.results['latency_min'] = latency_min
        self.results['latency_max'] = latency_max

    def get_yamable(self):
        return {'omg': {'sent': self.results['sent'],
                        'duration': self.results['duration'],
                        'received': self.results['received'],
                        'run_interval': self.run_interval,
                        'bandwidth': self.results['bandwidth'],
                        'success': self.results['success'],
                        }
                }


class OmgTest(TwoScriptTest):
    root = os.path.dirname(__file__)
    pre_run_script = os.path.join(root, "prepare.sh")
    run_script = os.path.join(root, "run.sh")
    test_res_class = OmgTestResults

    @classmethod
    def format_for_console(cls, data):
        sent = 0
        received = 0
        durations = []
        latencys = []
        latency_mins = []
        latency_maxs = []
        for node_res in data:
            for res in node_res:
                durations.append(res.results['duration'])
                received += res.results['received']
                sent += res.results['sent']
                latencys.append(res.results['latency'])
                latency_mins.append(res.results['latency_max'])
                latency_maxs.append(res.results['latency_min'])

        duration = max(durations)
        totalms = int(received / duration)
        sucess = int((received / sent) * 100)
        latency = sum(latencys) / len(latencys)
        latency_min = min(latency_mins)
        latency_max = max(latency_maxs)
        tab = texttable.Texttable(max_width=120)
        tab.set_deco(tab.HEADER | tab.VLINES | tab.BORDER)
        tab.header(["Bandwidth m/s", "Success %", "Total sent",
                    "Total received", "Latency", "Latency min", "Latency max",
                    "Duration"])
        tab.add_row([totalms, sucess, sent, received, latency, latency_min,
                     latency_max, duration])
        return tab.draw()
