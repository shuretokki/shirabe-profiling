# Licenses

This project uses the Apache-2.0 license. The full text is in [LICENSE](LICENSE).

This project began as a copy of [dataxid-profiling](https://github.com/dataxid/dataxid-profiling) 0.4.0 by DataXID, which also uses Apache-2.0.
The table below lists the other work that this project includes or loads.

## Third-party work

| Name | Used for | Copyright | License |
| --- | --- | --- | --- |
| IBM Plex Sans | Text font in the report | Copyright © 2017 IBM Corp. with Reserved Font Name "Plex" | SIL Open Font License 1.1 |
| Lilex | Code font in the report | Copyright 2019 The Lilex Project Authors | SIL Open Font License 1.1 |
| Lucide 0.469.0 | Icons in the report | Copyright Lucide Contributors 2022 and Cole Bemis 2013-2022 (Feather, MIT) | ISC |
| Almendra Italic | Letters of the logo wordmark | Copyright (c) 2011-2012, Ana Sanfelippo, with Reserved Font Name "Almendra" | SIL Open Font License 1.1 |
| Shippori Mincho Bold | Katakana of the logo wordmark | Copyright 2021 The Shippori Mincho Project Authors | SIL Open Font License 1.1 |
| Apache ECharts 5.5.1 | Charts in the report (loaded from a CDN) | Copyright 2017-2026 The Apache Software Foundation | Apache-2.0 |
| Tailwind CSS | Layout in the report (loaded from a CDN) | Copyright (c) Tailwind Labs, Inc. | MIT |

The Plex Sans and Lilex font files and their license texts are in `src/shirabe_profiling/report/templates/fonts/`.
The icon paths are in `src/shirabe_profiling/report/templates/icons.j2`.
The logo files in `assets/logo/` hold the outlines of the Almendra and Shippori Mincho letters as vector paths and no font file.
Their license texts are at [Almendra](https://github.com/google/fonts/blob/main/ofl/almendra/OFL.txt) and [Shippori Mincho](https://github.com/google/fonts/blob/main/ofl/shipporimincho/OFL.txt).
The report does not bundle ECharts or Tailwind CSS. The browser loads them when the report opens.
