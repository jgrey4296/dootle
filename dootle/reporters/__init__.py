"""
Different reporter implementation, inspired by:
https://archive.docs.dagger.io/0.9/sdk/elixir/756758/get-started/

❯ dagger run mix elixir_with_dagger.test
┣─╮
│ ▽ init
│ █ [0.76s] connect
│ ┣ [0.52s] starting engine
│ ┣ [0.18s] starting session
│ ┻
█ [1.75s] mix elixir_with_dagger.test
┃ Tests succeeded!
┣─╮
│ ▽ host.directory .
│ █ [0.23s] upload .
│ ┣ [0.15s] transferring eyJvd25lcl9jbGllbnRfaWQiOiIwNWNmN2E4YTF4dDZ0dG52amUwbG1yeTYxIiwicGF0aCI6Ii4iLCJpbmNsdWRlX3BhdHRlcm5zIjpudWxsLCJleGNsdWRlX3BhdHRlcm5zIjpbImRlcHMiLCJfYnVpbGQiXSwiZm9sbG93X3BhdGhzIjpudWxsLCJyZWFkX3NpbmdsZV9maWxlX29ubHkiOmZhbHNlLCJtYXhfZmlsZV9zaXplIjowfQ==:
│ █ CACHED copy . (exclude deps, _build)
│ ┣─╮ copy . (exclude deps, _build)
│ ┻ │
┣─╮ │
│ ▽ │ from hexpm/elixir:1.14.4-erlang-25.3.2-alpine-3.18.0
│ █ │ [0.18s] resolve image config for docker.io/hexpm/elixir:1.14.4-erlang-25.3.2-alpine-3.18.0
│ █ │ [0.04s] pull docker.io/hexpm/elixir:1.14.4-erlang-25.3.2-alpine-3.18.0
│ ┣ │ [0.04s] resolve docker.io/hexpm/elixir:1.14.4-erlang-25.3.2-alpine-3.18.0@sha256:d77ef43aeb585ec172e290c7ebc171a16e21ebaf7c9ed09b596b9db55c848f00
│ ┣─┼─╮ pull docker.io/hexpm/elixir:1.14.4-erlang-25.3.2-alpine-3.18.0
│ ┻ │ │
█◀──┴─╯ CACHED exec mix local.hex --force
█ CACHED exec mix local.rebar --force
█ CACHED exec mix deps.get
█ CACHED exec mix test
┻
• Engine: fd814943769d (version v0.8.7)
⧗ 2.51s ✔ 20 ∅ 5


"""

from .liner import LineReporter
