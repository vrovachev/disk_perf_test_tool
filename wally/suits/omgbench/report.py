import datetime
from StringIO import StringIO
import logging
from matplotlib import pyplot as plt
import numpy
import os
from scipy.interpolate import interp1d
import yaml
import jinja2

logger = logging.getLogger("wally")


def plot(x, ys, title, save_path, xticks):
    f = plt.figure()
    y_max = max([y.max() for y in ys.values()])
    plt.axis([min(x), max(x), 0, y_max + 20])
    ax1 = f.add_subplot(111)
    xn_ax = numpy.linspace(x[0], x[-1],
                           len(x)*10)
    ax1.set_title(title)
    for l, y in ys.items():
        yn_cor = interp1d(x, y,
                          kind='cubic')
        ax1.plot(xn_ax, yn_cor(xn_ax), label=l)
    display_timestamps = x[::(len(x) / 20 if
                              len(x) > 20
                              else 1)]
    plt.xticks(display_timestamps, xticks, size='small',
               rotation=70)
    plt.tight_layout()
    plt.xlabel('Timestamps')

    ax1.legend(loc='best', shadow=True)
    plt.savefig(save_path)
    plt.close()


def make_report(results_dir, sensor_storage, html_rep_name):
    if os.path.exists(html_rep_name):
        return
    # get all sensors data
    os.mkdir(os.path.join(results_dir, 'plots'))

    csvs = [f for f in os.listdir(sensor_storage) if f.endswith('.csv')]

    # get results
    resultsf = os.path.join(results_dir, 'raw_results.yaml')
    results = yaml.load(open(resultsf).read())


    span_size = 12 / len(results)
    node_sens_plot = {}

    sensors = {'cpu': ['us', 'sy', 'id', 'wa', 'st'],
               'mem': ['swpd', 'free', 'buff', 'cache'],
               'io': ['bi', 'bo'],
               'swap': ['si', 'so'],
               'system': ['in', 'cs'],
               'procs': ['r', 'b']}

    results_l = []
    for test_name, res in results:
        omg_res = {'received': 0, 'sent': 0, 'duration': 0, 'sucess': 0,
                   'bandwidth': 0}
        for one in res[0]:
            omg_res['received'] += one['omg']['received']
            omg_res['sent'] += one['omg']['sent']
            if one['omg']['duration'] > omg_res['duration']:
                omg_res['duration'] = one['omg']['duration']
        omg_res['success'] = int(omg_res['received'] / omg_res['sent'] * 100)
        omg_res['bandwidth'] = omg_res['received'] / omg_res['duration']
        omg_res['name'] = test_name
        results_l.append(omg_res)

        startt = str(res[0][0]['omg']['run_interval'][0]).partition('.')[0]
        csvs_for_test = [
            csv for csv in csvs if
            (csv.startswith(startt[:-2]) or
             csv.startswith(str(int(startt) - 1)))][0]

        sensors_data = os.path.join(sensor_storage, csvs_for_test)
        node_sensors_data = [d for d in
                             open(sensors_data).read().split('NEW_DATA') if
                             d.strip()]
        for node_data in node_sensors_data:
            node = node_data.split(',')[1]
            data = numpy.genfromtxt(StringIO(node_data), delimiter=',',
                                    skip_header=2,
                                    dtype=int, autostrip=True,
                                    converters={4: lambda s: float(s or 0)})
            headers = open(sensors_data).read()
            headers = [header.strip() for header in
                       headers.split('\n')[1].split(',')][1:]

            d = dict(zip(headers, zip(*data.tolist())))

            timestamps = d['fuel.domain.tld']
            timestampsd = numpy.array(timestamps)
            times = [datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                     for ts in timestampsd]

            for sens_name, sens in sensors.items():
                title = sens_name
                plotd = dict([(s, numpy.array(d[s])) for s in sens])
                fname = os.path.join(results_dir,
                                     'plots/test-%s-%s-%s.svg' % (node,
                                                                  test_name,
                                                                  title))
                plot(timestamps, plotd, title, fname, times)
                node_sens_plot.setdefault(node, {})
                node_sens_plot[node].setdefault(test_name, {})
                node_sens_plot[node][test_name][title] = fname

    env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
    template = env.get_template('wally/suits/omgbench/report.html')
    output_from_parsed_template = template.render(results=results_l,
                                                  nodes=node_sens_plot,
                                                  span_size=span_size,
                                                  )
    # to save the results
    with open(html_rep_name, "w+") as f:
        f.write(output_from_parsed_template)

    logger.info("HTML report stored in %s" % html_rep_name)
