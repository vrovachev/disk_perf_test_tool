import os.path


import texttable


from ..itest import TwoScriptTest
from ..itest import TestResults


class OmgTestResults(TestResults):

    def __init__(self, config, results, raw_result, run_interval):
        super(OmgTestResults, self).__init__(config, results, raw_result,
                                             run_interval)
        self.parse()

    def parse(self):
        res_list = self.raw_result.strip().split('\n')
        self.results = dict()
        self.results['sent'] = float(res_list[0])
        self.results['duration'] = int(res_list[1])
        self.results['received'] = sum([int(r) for r in res_list[2:]])
        self.results['bandwidth'] = self.results['received'] / \
                                    self.results['duration']
        self.results['success'] = int(self.results['sent']
                                      / self.results['received'] * 100)

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
        for res in data[0]:
            res_list = res.raw_result.strip().split('\n')
            sent = float(res_list[0])
            duration = int(res_list[1])
            received = sum([int(r) for r in res_list[2:]])

        totalms = int(received / duration)
        sucess = int((received / sent) * 100)
        tab = texttable.Texttable(max_width=120)
        tab.set_deco(tab.HEADER | tab.VLINES | tab.BORDER)
        tab.header(["Bandwidth m/s", "Success %", "Total sent",
                    "Total received"])
        tab.add_row([totalms, sucess, sent, received])
        return tab.draw()
