### Interop extras

- Five new optional extras each install one conversion target for the
  `pietto.interop` adapters, pinned exactly: `interop-pandas` installs
  `pandas==3.1.1`, `interop-polars` installs `polars==2.1.0` (which itself
  pins `polars-runtime-32==2.1.0`), `interop-numpy` installs `numpy==2.5.4`,
  `interop-scipy` installs `scipy==1.18.1` and `interop-matplotlib` installs
  `matplotlib==3.11.2`. Each extra pins only its target library; NumPy and
  the targets' other dependencies come from the targets' own requirements.
  There is no combined extra.
- An interop extra installs no PyArrow, so install it beside `arrow`, for
  example `pip install "pietto[arrow,interop-pandas]"`. Only the pins are
  qualified, as `pietto[arrow,interop-X]` for each of the five extras on
  CPython 3.12 and 3.13, Linux x86-64, glibc 2.28 or later. Another route
  extra beside an interop extra is covered only on the assumption that it
  carries the same PyArrow `26.0.1`. Windows, macOS and CPython 3.14 are not
  claimed.
- The core install is unchanged and still needs no PyArrow or target
  library; the package metadata lists the five new extras.
