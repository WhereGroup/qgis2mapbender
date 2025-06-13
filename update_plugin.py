import subprocess
from typing import List

import click

def _call_pb_tool():
    command = ['C:\\Users\\pf\\AppData\\Roaming\\Python\\Python312\\Scripts\\pb_tool']
    command.extend(['deploy', '-y', '--config_file', 'C:\\prjs\\QGIS2Mapbender\\plugin\\QGIS2Mapbender\\pb_tool.cfg'])
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        out = p.stdout.read()
        err = p.stderr.read()

        click.echo(out.decode())
        click.secho(err.decode(), fg="red")


if __name__ == '__main__':
    _call_pb_tool()
