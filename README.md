# Solana Multitool

A non-complete toolkit for various things

what works (mostly)
  - getting swaps by program id
  - parsing said swaps (done in go forked from [franco-bianco/solanaswap-go](https://github.com/franco-bianco/solanaswap-go))

what doesn't work (yet)
  - scanning dexes for pool creation events
  - getting creation event given a pool

plan:
  - scan from beginning of sol history and recognise when new pool is created
  - index swaps with the pool

## Getting started

in the root /config/ copy the .env.example to .env with your own rpc endpoint
build getswaps.go and move it to the /bin/ folder
use the python files to achieve desired outcome

## How to use the Tools

todo:
  - implement thorough testing
  - documentation properly
  - stop defaults being defined in multiple places
