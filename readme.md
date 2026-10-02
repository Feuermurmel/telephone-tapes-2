# telephone-tapes-2

Downloads the [Group 1 Playlist](https://evan-doorbell.com/group-1-playlist/) from
[Evan Doorbell's Phone Tapes](https://evan-doorbell.com/) and converts them to `.m4b`
audio book files.

Successor to [`telephone-tapes`](https://github.com/Feuermurmel/telephone-tapes).

## Development

### Setup

The project uses [pre-commit](https://pre-commit.com) to run source code formatters and
type checking before commit. A Makefile target is provided to create a virtualenv ready
for development:

```shell
pre-commit install
make venv
. venv/bin/activate
```

### Type Checking

Type checking can be run using [mypy](https://github.com/python/mypy):

```bash
mypy
```
