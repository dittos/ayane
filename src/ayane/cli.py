import collections
import os
import click
from ayane.storage.win_wpd import Wpd


def main():
    cli()


@click.group()
@click.pass_context
def cli(ctx):
    wpd = Wpd()
    devices = wpd.get_devices()
    if not devices:
        click.echo('No available storage found.')
        ctx.abort()
    if len(devices) == 1:
        device = devices[0]
    else:
        for i, device in enumerate(devices):
            click.echo('[{0}] {1: <30} {2} {3}'.format(
                i,
                device.get_friendly_name(),
                device.get_manufacturer(),
                device.get_description(),
            ))
        selected = click.prompt('Multiple storages found. Please choose one', type=int)
        device = devices[selected]

    device.open()
    ctx.obj = {
        'device': device,
    }


@cli.command()
@click.argument('path', default='')
@click.pass_context
def ls(ctx, path):
    device = ctx.obj['device']
    parent = resolve_path(device, path)

    for obj in device.iter_objects(parent=parent):
        name = obj.name
        if obj.is_folder:
            name += '/'
        click.echo(u'{}\t{}'.format(obj.id, name))


@cli.command()
@click.argument('path')
@click.pass_context
def stats(ctx, path):
    device = ctx.obj['device']
    parent = resolve_path(device, path)

    size_by_ext = collections.defaultdict(lambda: 0)
    queue = [parent]
    while queue:
        p = queue.pop()
        w, h = click.get_terminal_size()
        click.echo(u'\r@ ' + p.name[:w // 2], nl=False)
        for obj in device.iter_objects(parent=p):
            if obj.is_folder:
                queue.append(obj)
            else:
                _, ext = os.path.splitext(obj.name)
                ext = ext.lower()
                size_by_ext[ext] += obj.size

    click.echo('\r')
    for ext, size in sorted(size_by_ext.items(), key=lambda (ext, size): size, reverse=True):
        click.echo(u'{}\t{}'.format(ext, filesizeformat(size)))


def resolve_path(device, path):
    # TODO: escape, ...
    parts = path.split('/')
    parent = None
    for part in parts:
        next_parent = None
        for obj in device.iter_objects(parent=parent):
            if obj.name == part:
                next_parent = obj
                break
        if next_parent is None:
            return None
        parent = next_parent

    return parent


def filesizeformat(bytes_):
    """
    Formats the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
    102 bytes, etc.).
    """
    try:
        bytes_ = float(bytes_)
    except (TypeError, ValueError, UnicodeDecodeError):
        return "0 bytes"

    def filesize_number_format(value):
        return '{:g}'.format(round(value, 1))

    KB = 1 << 10
    MB = 1 << 20
    GB = 1 << 30
    TB = 1 << 40
    PB = 1 << 50

    negative = bytes_ < 0
    if negative:
        bytes_ = -bytes_  # Allow formatting of negative numbers.

    if bytes_ < KB:
        unit = 'byte' if bytes_ == 1 else 'bytes'
        value = "{:g} {}".format(bytes_, unit)
    elif bytes_ < MB:
        value = "%s KB" % filesize_number_format(bytes_ / KB)
    elif bytes_ < GB:
        value = "%s MB" % filesize_number_format(bytes_ / MB)
    elif bytes_ < TB:
        value = "%s GB" % filesize_number_format(bytes_ / GB)
    elif bytes_ < PB:
        value = "%s TB" % filesize_number_format(bytes_ / TB)
    else:
        value = "%s PB" % filesize_number_format(bytes_ / PB)

    if negative:
        value = "-%s" % value
    return value
