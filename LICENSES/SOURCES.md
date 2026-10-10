# Sources of the license texts

Each license text in this directory is a byte-for-byte copy of the upstream
file, or of the line range stated for it, at the commit, archive snapshot or
tracked artifact listed below, retrieved on 2026-10-10 (UTC).

Three upstream details:

- The ANTLR 3.5.3 tag has no license file at the repository root or for the
  Java runtime (`runtime/Java`, `org.antlr:antlr-runtime`) that the ANTLR jar
  bundles. The closest text at that tag is `tool/LICENSE.txt`, copied here. The
  runtime's own source headers read "Copyright (c) 2005-2009 Terence Parr"
  (one file: 2012 Terence Parr, 2012 Sam Harwell).
- The TreeLayout 1.0.3 tag ships a BSD license text, while its POM names
  BSD-3-Clause with a URL to the abego Public Licence 1.0 page. Both texts are
  kept.
- Pietto's generated parser follows ANTLR's Python3 code-generation template.
  That template's own BSD header differs from the ANTLR 4.13.2 `LICENSE.txt`, so
  it is copied separately from the tracked ANTLR jar.

| File | Upstream file | Pin | SHA-256 |
| --- | --- | --- | --- |
| `ANTLR-4.13.2.txt` | `https://github.com/antlr/antlr4/blob/cc82115a4e7f53d71d9d905caa2c2dfa4da58899/LICENSE.txt` (tag `4.13.2`) | commit `cc82115a4e7f53d71d9d905caa2c2dfa4da58899` | `3db1fb3ee79a4b4f9918fc4d0f6133bf18a3cf787f126cd22f8aa9b862281c0c` |
| `ANTLR-4.13.2-Python3-template-header.txt` | Lines 1-30 of `org/antlr/v4/tool/templates/codegen/Python3/Python3.stg` inside `tools/antlr-4.13.2-complete.jar` (entry SHA-256 `87df5899ff72d31e9371cbda58c37e7f17a27469b85753d228243b44034dd576`) | jar SHA-256 `eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76` | `3bad51e28a4ecebcb8b9afdddf3bf38ef8279bc9349fa0102850ee0453a30b65` |
| `ANTLR-3.5.3.txt` | `https://github.com/antlr/antlr3/blob/0519032bb167b37f206968d9037753ad655a2623/tool/LICENSE.txt` (tag `3.5.3`) | commit `0519032bb167b37f206968d9037753ad655a2623` | `95fc87cbe29814a32fc97f6f8eb7ae55e4816d4b75143635c4db736e7e374fa2` |
| `StringTemplate-4.3.4.txt` | `https://github.com/antlr/stringtemplate4/blob/a2c4ef074e7c5018c7eb46372ed07f756c140404/LICENSE.txt` (tag `ST4-4.3.4`) | commit `a2c4ef074e7c5018c7eb46372ed07f756c140404` | `022bdae9c4f408d375f8c3c16b7695c22a2152c56535af180059e3ab92adffb0` |
| `TreeLayout-1.0.3.txt` | `https://github.com/abego/treelayout/blob/fb5b5326d9fe642b9ca0631c3da739bf775f6374/org.abego.treelayout/src/LICENSE.TXT` (tag `v1.0.3`) | commit `fb5b5326d9fe642b9ca0631c3da739bf775f6374` | `b6fcaaa79c777ccd16e7493a0451eeaca22d7166782d1b962b49af410ed09e4f` |
| `TreeLayout-1.0.3-abego-apl-v10.html` | `https://web.archive.org/web/20120110233643id_/http://www.abego-software.de:80/legal/apl-v10.html` (the licence URL named by the TreeLayout 1.0.3 POM) | Wayback snapshot `20120110233643` | `739ce194643e13015a29fb61567edad3dd80dd4df94a73ebefbd7d4606133164` |
| `ICU-72.1.txt` | `https://github.com/unicode-org/icu/blob/ff3514f257ea10afe7e710e9f946f68d256704b1/icu4j/main/shared/licenses/LICENSE` (tag `release-72-1`) | commit `ff3514f257ea10afe7e710e9f946f68d256704b1` | `af3e84c401f1a35e8d32d6eb1a33fe587c3981aa5cd206033d9527c1855b57a2` |
| `pgvector-0.8.6.txt` | `https://github.com/pgvector/pgvector/blob/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/LICENSE` (tag `v0.8.6`) | commit `8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c` | `6bba9ebeb73e27477463b05e5ef1bf303bccbddb3db9bbc95905d351604d6a87` |
| `PostgreSQL-18.6.txt` | `https://github.com/postgres/postgres/blob/724edf9bde9d356724ad384a2e196edc3c9f80f7/COPYRIGHT` (tag `REL_18_6`) | commit `724edf9bde9d356724ad384a2e196edc3c9f80f7` | `3d6af92ff8a4c2cdf69afb1cf44edea727922f5cd0cf8b5f72b11cdecac8fdfd` |
| `PostGIS-3.6.4-LICENSE.txt` | `https://github.com/postgis/postgis/blob/94d984bd083635c1d253db0f87cf80b32548e406/LICENSE.TXT` (tag `3.6.4`) | commit `94d984bd083635c1d253db0f87cf80b32548e406` | `81749eea887e78402c9b85896cd629b155bc29256927f818f01001f038146391` |
| `PostGIS-3.6.4-COPYING.txt` | `https://github.com/postgis/postgis/blob/94d984bd083635c1d253db0f87cf80b32548e406/COPYING` (tag `3.6.4`) | commit `94d984bd083635c1d253db0f87cf80b32548e406` | `8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643` |
