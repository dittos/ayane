# Ayane

## Supported platforms

* Windows

## Usage

If only one device is connected on the system, it is used automatically. Otherwise, choose prompt will be shown.

### List files

```
> ayane ls
Phone
RenderingInformation
```

```
> ayane ls Phone
Android/
Music/
Podcasts/
...
```

### File size stats by extension

```
> ayane stats Phone/Music
.mp3    5.1 GB
.flac   4.1 GB
.m4a    739 MB
.ape    297.4 MB
.ogg    237.1 MB
.wav    140.8 MB
.bmp    101.9 MB
.rar    10 MB
.asd    2.2 MB
.nfo    18.1 KB
.txt    16.5 KB
.log    6.2 KB
.html   5.6 KB
.cue    4.2 KB
.url    118 bytes
Total   10.7 GB
```

### Remove files not matching whitelisted extension / max. duration

```
> ayane trim Phone/Music -k mp3 -k flac -k m4a -k ogg -k wav -m 600000
.ape    297.4 MB
.bmp    101.9 MB
Total   399.4 MB
Found 22 objects to delete. Continue? [y/N]: y
  [####################################]  100%
```
