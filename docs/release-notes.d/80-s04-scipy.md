### SciPy CSR arrays from a batch

`pietto.interop.to_scipy_csr(batch, row, column, value, shape)` returns a
canonical `scipy.sparse.csr_array` with one stored entry per record: the
`row` and `column` fields give its coordinate and the `value` field its value.
Explicit zeros stay stored, column indices are sorted within each row, the
index and index-pointer arrays are int32, and the data keeps the value
field's width (int16, int32 or int64), so the same records in any order give
the same arrays. A typed empty batch gives an array of the given shape with no
entries, and the array stays usable after the batch is closed.

A repeated coordinate is refused with `ValueError`, never summed, and so is a
SciPy result of another type, shape, index dtype, data width, entry count or
index order. Install it with `pietto[arrow,interop-scipy]` (`scipy==1.18.1`).
