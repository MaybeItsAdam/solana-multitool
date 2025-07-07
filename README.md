# Solana Multitool

A non-complete toolkit for various things

what works
  - getting swaps by program id
  - parsing said swaps (done in go forked from [franco-bianco/solanaswap-go](https://github.com/franco-bianco/solanaswap-go))
  - scanning solana blocks and filtering by account keys or log messages -> can be used to find pool creation events

todos:
  - or bundle golang binaries using importlib
  - user config - use pydantic_settings

## Getting started

in the root /config/ copy the .env.example to .env with your own rpc endpoint
run build.sh to compile the golang binary
build getswaps.go and move it to the /bin/ folder
use the python files to achieve desired outcome

## How to use the Tools

put docs here
