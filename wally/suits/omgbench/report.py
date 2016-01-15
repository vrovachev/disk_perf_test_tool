import datetime
from StringIO import StringIO
import logging
from matplotlib import pyplot as plt
import numpy
import os
from scipy.interpolate import interp1d
import yaml


logger = logging.getLogger("wally")


template = """
<!DOCTYPE html>
<html>
    <head>
        <title>Omgbench Report</title>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js"></script>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">
    </head>
    <body>
        <div class="page-header text-center">
            <h2>Omgbench Report</h2>
        </div>
        <h3>Test results</h3>
        %s
        <h3>Sensors data</h3>
        %s
    </body>
</html>
"""


def make_report(cfg, html_rep_name):
    if os.path.exists(html_rep_name):
        return
    # get all sensors dat
    os.mkdir(os.path.join(cfg.results_dir, 'plots'))

    csvs = [f for f in os.listdir(cfg.sensor_storage) if f.endswith('.csv')]

    # get results
    resultsf = os.path.join(cfg.results_dir, 'raw_results.yaml')
    results = yaml.load(open(resultsf).read())

    res_template = """
    <div>
    <table class="table table-hover">
    <thead>
    <tr>
    <th>Test name</th><th>Duration</th><th>Received</th><th>Sent</th><th>Success</th><th>Bandwidth</th>
    </tr>
    </thead>
    </tbody>
    <tr>
    <td>%(name)s</td><td>%(duration)s</td><td>%(received)s</td><td>%(sent)s</td><td>%(success)s &#37;</td><td>%(bandwidth)s msg&#47;s</td>
    </tr>
    </tbody>
     </table>
     </div>"""
    spans = []
    span_size = 12 / len(results)
    node_sens_plot = {}

    sensors = ['eth0.recv_bytes', 'eth0.send_bytes', 'cpu.procs_queue']

    divs_res = []
    for test_name, res in results:
        omg_res = res[0][0]['omg']
        omg_res['name'] = test_name
        divs_res.append(res_template % omg_res)
        startt = str(omg_res['run_interval'][0]).partition('.')[0]
        csvs_for_test = [csv for csv in csvs if csv.startswith(startt[:-1])][0]

        sensors_data = os.path.join(cfg.sensor_storage, csvs_for_test)
        node_sensors_data = [d for d in
                             open(sensors_data).read().split('NEW_DATA') if d.strip()]
        for node_data in node_sensors_data:
            node = node_data.split(',')[1]
            data = numpy.genfromtxt(StringIO(node_data), delimiter=',',
                                    skip_header=2,
                                    dtype=int, autostrip=True,
                                    converters={4: lambda s: float(s or 0)})
            headers = open(sensors_data).read()
            headers = headers.split('\n')[1].split(',')[1:]

            d = zip(headers, *data.tolist())

            timestamps = d.pop(0)[1:]
            timestampsd = numpy.array(timestamps)
            times = [datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                     for ts in timestampsd]
            for i in range(len(d)):
                title = d[i][0]
                if title not in sensors:
                    continue
                f = plt.figure()
                y = numpy.array(d[i][1:])
                plt.axis([min(timestamps), max(timestamps), 0, y.max() + 20])
                ax1 = f.add_subplot(111)
                xn_ax = numpy.linspace(timestamps[0], timestamps[-1],
                                       len(timestamps)*10)
                yn_cor = interp1d(timestamps, numpy.array(d[i][1:]),
                                  kind='cubic')
                ax1.set_title(title)
                ax1.plot(xn_ax, yn_cor(xn_ax))
                display_timestamps = timestamps[::(len(timestamps) / 20 if
                                                   len(timestamps) > 20
                                                   else 1)]
                plt.xticks(display_timestamps, times, size='small',
                           rotation=70)
                plt.tight_layout()
                plt.xlabel('Timestamps')

                fname = os.path.join(cfg.results_dir,
                                     'plots/test-%s-%s.svg' % (test_name,
                                                               d[i][0]))
                plt.savefig(fname)
                plt.close()

                node_sens_plot.setdefault(node, {})
                node_sens_plot[node].setdefault(test_name, {})
                node_sens_plot[node][test_name][title] = fname

    accordion_cont = """
    <div class="panel-group" id="accordion" role="tablist" aria-multiselectable="true">%s</div>
    """
    accordion_item = """ <div class="panel panel-default">
<div class="panel-heading" role="tab" id="heading%(i)s">
  <h4 class="panel-title">
    <a role="button" data-toggle="collapse" data-parent="#accordion" href="#collapse%(i)s" aria-expanded="true" aria-controls="collapse%(i)s">
      %(node)s
    </a>
  </h4>
</div>
<div id="collapse%(i)s" class="panel-collapse collapse in" role="tabpanel" aria-labelledby="heading%(i)s">
  <div class="panel-body">
  %(data)s
  </div>
</div>
</div>"""
    acc_items = []
    i = 0
    for node, sensors in node_sens_plot.items():
        i += 1
        spans = []
        span = '<div class="col-md-' + str(span_size) + '">%s</div>'
        for test_name, sens_data in sensors.items():
            divs = []
            for plot in sens_data.values():
                div = "<div><img src='%s'></div>" % plot
                divs.append(div)
            spans.append(span % ''.join(divs))
        acc_items.append(accordion_item % {'i': i, 'node': node,
                                           'data': ''.join(spans)})

    accordion = accordion_cont % ''.join(acc_items)

    with open(html_rep_name, "w+") as f:
        f.write(template % (''.join(divs_res), accordion))

    logger.info("HTML report stored in %s" % html_rep_name)
