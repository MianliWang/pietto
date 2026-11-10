# Fresh local closure

From this directory, run the exact no-database command below. It creates a
fresh candidate patch and TLS directory, writes `fresh-binding.json`, source
SHA-256 values, logs and exit files here, then runs only the fabricated judge.

```bash
ROOT=$(pwd -P)
PIETTO_PG_RUN_ROOT="$ROOT" PIETTO_PG_PYTHON="$ROOT/../../../runtime/venvs/native/bin/python" PIETTO_PG_CANDIDATE="$ROOT/../../../candidates/maintenance" PIETTO_PG_WHEEL="$ROOT/../../../runtime/dist/pietto-0.1.10-py3-none-any.whl" PIETTO_PG_WHEEL_SHA256=f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73 PIETTO_PG_BASE=f8ccd2c44a2d9adf431a496bd9bbae037783176f PIETTO_PG_PATCH_SHA256=548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc PIETTO_PG_LOCK_SHA256=b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064 bash "$ROOT/fresh-start.sh"
```

It does not start Docker, a database, or a network operation. Database execution remains a separately authorized later action.
After that authorization, from this same directory, the exact target command is:

```bash
ROOT=$(pwd -P)
PIETTO_PG_RUN_ROOT="$ROOT" PIETTO_PG_PYTHON="$ROOT/../../../runtime/venvs/native/bin/python" PIETTO_PG_CANDIDATE="$ROOT/../../../candidates/maintenance" PIETTO_PG_WHEEL="$ROOT/../../../runtime/dist/pietto-0.1.10-py3-none-any.whl" PIETTO_PG_WHEEL_SHA256=f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73 PIETTO_PG_BASE=f8ccd2c44a2d9adf431a496bd9bbae037783176f PIETTO_PG_PATCH_SHA256=548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc PIETTO_PG_LOCK_SHA256=b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064 PIETTO_PG_IMAGE=sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e bash "$ROOT/target-run.sh"
```

It holds only `/tmp/claude-1000/pietto-docker-campaign-postgres.lock`, sets a
fresh nonce-derived container identity, and wraps the complete campaign in
`timeout 7200`.
