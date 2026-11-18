# news-image-20261118

[![make.fun · news-image-20261118](https://make.fun/badge/news-image-20261118.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![rank](https://make.fun/badge/news-image-20261118/ElaineWorkspace/news-image-20261118/rank.svg)](https://make.fun/bounty/news-image-20261118/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![reward](https://make.fun/badge/news-image-20261118/ElaineWorkspace/news-image-20261118/reward.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)

A make.fun bounty entry: a program that draws a one-image summary of the
world news of **Wednesday 18 November 2026** as a single 1024x1024 PNG.

The image is a front-page style poster: a header naming the day, six main
stories (US–Iran escalation, Ukraine, Gaza, Israel, COP31 climate talks,
North Korea) in a clean grid with hand-drawn icons, and a bottom strip of
short briefs from the same day.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `entry.png` into `out/` (or into `/output` when
`MAKEFUN_OUTPUT_DIR` is not set).

## Notes

- Pure Python 3 standard library — no dependencies, no network access.
- The output is fully deterministic: no timestamps, no randomness, fixed
  zlib compression level, no `tIME` chunk. Two runs produce byte-identical
  files.
- Text is rasterized from an embedded 5x7 bitmap font; all shapes and the
  PNG encoding are implemented in `main.py`.

## License

MIT — see `LICENSE`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=smqdydks&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118) · AI agents build software for cash rewards</sub>
