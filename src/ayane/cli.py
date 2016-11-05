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
def rm(ctx, path):
    device = ctx.obj['device']
    obj = resolve_path(device, path)
    device.delete_objects([obj])


@cli.command()
@click.argument('path')
@click.pass_context
def stats(ctx, path):
    device = ctx.obj['device']
    parent = resolve_path(device, path)

    total_size = 0
    size_by_ext = collections.defaultdict(lambda: 0)
    for path, folders, objs in walk(device, parent):
        echo_clear_line(u'@ ' + path)
        for obj in objs:
            _, ext = os.path.splitext(obj.name)
            ext = ext.lower()
            total_size += obj.size
            size_by_ext[ext] += obj.size
    echo_clear_line()

    for ext, size in sorted(size_by_ext.items(), key=lambda (ext, size): size, reverse=True):
        click.echo(u'{}\t{}'.format(ext, filesizeformat(size)))
    click.echo(u'Total\t{}'.format(filesizeformat(total_size)))


@cli.command()
@click.argument('path')
@click.option('--delete-ext', '-d', multiple=True)
@click.pass_context
def trim(ctx, path, delete_ext):
    device = ctx.obj['device']
    parent = resolve_path(device, path)
    delete_ext_set = set()
    for ext in delete_ext:
        ext = ext.lower()
        if ext[0] != '.':
            ext = '.' + ext
        delete_ext_set.add(ext)

    objs_to_delete = []
    total_size = 0
    size_by_ext = collections.defaultdict(lambda: 0)
    for path, folders, objs in walk(device, parent):
        echo_clear_line(u'@ ' + path)
        for obj in objs:
            _, ext = os.path.splitext(obj.name)
            ext = ext.lower()
            if ext in delete_ext_set:
                objs_to_delete.append(obj)
                total_size += obj.size
                size_by_ext[ext] += obj.size
    echo_clear_line()

    for ext, size in sorted(size_by_ext.items(), key=lambda (ext, size): size, reverse=True):
        click.echo(u'{}\t{}'.format(ext, filesizeformat(size)))
    click.echo(u'Total\t{}'.format(filesizeformat(total_size)))

    click.confirm('Found {} objects to delete. Continue?'.format(len(objs_to_delete)), abort=True)
    with click.progressbar(objs_to_delete) as objs:
        for obj in objs:
            device.delete_objects([obj])


def echo_clear_line(line=''):
    w, h = click.get_terminal_size()
    click.echo('\r' + ' ' * w, nl=False)
    if line:
        click.echo(u'\r' + line[:w // 2], nl=False)
    else:
        click.echo()


def resolve_path(device, path):
    # TODO: escape, ...
    parts = path.rstrip('/').split('/')
    current = None
    for part in parts:
        found = None
        for obj in device.iter_objects(parent=current):
            if obj.name == part:
                found = obj
                break
        if found is None:
            return None
        current = found

    return current


def walk(device, parent):
    queue = [(parent, parent.name)]
    while queue:
        folder, path = queue.pop()
        folders = []
        objs = []
        for obj in device.iter_objects(parent=folder):
            if obj.is_folder:
                folders.append(obj)
            else:
                objs.append(obj)
        yield path, folders, objs
        queue.extend((f, path + u'/' + f.name) for f in folders)


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
