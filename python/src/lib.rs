use pyo3::prelude::*;
use pyo3::types::{PyDate, PyDateAccess, PyDateTime, PyDict, PyList, PyTimeAccess};
use streamxl_core::dates;
use streamxl_core::sheet_parser::{CellMetadata, CellValue};
use streamxl_core::stream::{RowIter, RowIterMetadata};
use streamxl_core::writer::WriteCell;
use streamxl_core::{XlsxStream, XlsxWriter};

// ── Reading ───────────────────────────────────────────────────────────────────

fn cell_to_pyobject(py: Python<'_>, cell: &CellValue) -> PyResult<PyObject> {
    match cell {
        CellValue::String(s) => Ok(s.clone().into_pyobject(py)?.into_any().unbind()),
        CellValue::Number(n) => Ok(n.into_pyobject(py)?.into_any().unbind()),
        CellValue::Bool(b) => Ok(b.into_pyobject(py)?.as_any().clone().unbind()),
        CellValue::Date(n) => {
            let (year, month, day) = dates::serial_to_date(*n as u32);
            Ok(PyDate::new(py, year, month as u8, day as u8)?
                .into_any()
                .unbind())
        }
        CellValue::DateTime(n) => {
            let (year, month, day, hour, min, sec, us) = dates::serial_to_datetime(*n);
            Ok(PyDateTime::new(
                py,
                year,
                month as u8,
                day as u8,
                hour as u8,
                min as u8,
                sec as u8,
                us,
                None,
            )?
            .into_any()
            .unbind())
        }
        CellValue::Error(e) => Ok(e.clone().into_pyobject(py)?.into_any().unbind()),
        CellValue::Empty => Ok(py.None()),
    }
}

fn metadata_to_pydict(py: Python<'_>, metadata: &CellMetadata) -> PyResult<Py<PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("value", cell_to_pyobject(py, &metadata.value)?)?;

    if let Some(formula) = &metadata.formula {
        dict.set_item("formula", formula)?;
    } else {
        dict.set_item("formula", py.None())?;
    }

    if let Some(formula_type) = &metadata.formula_type {
        dict.set_item("formula_type", formula_type)?;
    } else {
        dict.set_item("formula_type", py.None())?;
    }

    if let Some(comment) = &metadata.comment {
        dict.set_item("comment", comment)?;
    } else {
        dict.set_item("comment", py.None())?;
    }

    if let Some(author) = &metadata.comment_author {
        dict.set_item("comment_author", author)?;
    } else {
        dict.set_item("comment_author", py.None())?;
    }

    Ok(dict.into())
}

#[pyfunction]
#[pyo3(signature = (path, sheet = None))]
fn read(py: Python<'_>, path: &str, sheet: Option<&str>) -> PyResult<Py<PyList>> {
    let stream = XlsxStream::open(path, sheet)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let result = PyList::empty(py);
    let rows = stream
        .rows()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    for row_result in rows {
        let row = row_result
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let py_row = PyList::empty(py);
        for cell in &row {
            py_row.append(cell_to_pyobject(py, cell)?)?;
        }
        result.append(py_row)?;
    }
    Ok(result.into())
}

#[pyfunction]
#[pyo3(signature = (path, sheet = None))]
fn read_with_metadata(py: Python<'_>, path: &str, sheet: Option<&str>) -> PyResult<Py<PyList>> {
    let stream = XlsxStream::open(path, sheet)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let result = PyList::empty(py);
    let rows = stream
        .rows_with_metadata()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    for row_result in rows {
        let row = row_result
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let py_row = PyList::empty(py);
        for cell in &row {
            py_row.append(metadata_to_pydict(py, cell)?)?;
        }
        result.append(py_row)?;
    }
    Ok(result.into())
}

#[pyfunction]
fn sheets(path: &str) -> PyResult<Vec<String>> {
    XlsxStream::sheet_names(path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}

fn dxf_to_pydict(py: Python<'_>, dxf: &streamxl_core::DxfFormat) -> PyResult<Py<PyDict>> {
    let d = PyDict::new(py);
    d.set_item("font_color", &dxf.font_color)?;
    d.set_item("font_bold", dxf.font_bold)?;
    d.set_item("font_italic", dxf.font_italic)?;
    d.set_item("fill_bg_color", &dxf.fill_bg_color)?;
    d.set_item("fill_fg_color", &dxf.fill_fg_color)?;
    Ok(d.into())
}

#[pyfunction]
#[pyo3(signature = (path, sheet = None))]
fn conditional_formats(py: Python<'_>, path: &str, sheet: Option<&str>) -> PyResult<Py<PyList>> {
    let stream = XlsxStream::open(path, sheet)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let result = PyList::empty(py);
    for rule in stream.conditional_formats() {
        let d = PyDict::new(py);
        d.set_item("sqref", &rule.sqref)?;
        d.set_item("type", &rule.rule_type)?;
        d.set_item("operator", &rule.operator)?;
        d.set_item("formulas", &rule.formulas)?;
        d.set_item("priority", rule.priority)?;
        d.set_item("stop_if_true", rule.stop_if_true)?;
        match &rule.format {
            Some(dxf) => d.set_item("format", dxf_to_pydict(py, dxf)?)?,
            None => d.set_item("format", py.None())?,
        }
        result.append(d)?;
    }
    Ok(result.into())
}

// ── Streaming (real backpressure, real O(1) memory) ────────────────────────
//
// `read()`/`read_with_metadata()` above eagerly materialize an entire sheet
// into a Python list before returning. `PyRowIter`/`PyRowIterMetadata` below
// expose the Rust-level `RowIter`/`RowIterMetadata` (core/src/stream.rs)
// directly as real Python iterators (`__iter__`/`__next__`). A Python `for
// row in stream_rows(path):` loop only pulls one row into Python memory at a
// time, and -- since `RowIter`/`RowIterMetadata` decompress and parse the
// sheet XML incrementally rather than buffering it whole (see
// ROADMAP_HONEST.md gap #10) -- the Rust side stays O(1) memory too, not
// just the Python-list-shape. `RowIter`/`RowIterMetadata` own their own
// `ZipArchive` + decompressing reader (no lifetime tied to an `XlsxStream`),
// so no self-referential wrapping is needed here.

/// Real streaming row iterator: `for row in stream_rows(path):` holds only
/// one row in memory at a time, on both the Python and Rust sides.
#[pyclass(unsendable)]
struct PyRowIter {
    inner: RowIter,
}

#[pymethods]
impl PyRowIter {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>, py: Python<'_>) -> PyResult<Option<Py<PyList>>> {
        match slf.inner.next() {
            None => Ok(None),
            Some(Err(e)) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
            Some(Ok(row)) => {
                let py_row = PyList::empty(py);
                for cell in &row {
                    py_row.append(cell_to_pyobject(py, cell)?)?;
                }
                Ok(Some(py_row.into()))
            }
        }
    }
}

/// Real streaming row+metadata iterator (formulas, comments, etc.) -- same
/// one-row-at-a-time backpressure and O(1) memory as `PyRowIter`.
#[pyclass(unsendable)]
struct PyRowIterMetadata {
    inner: RowIterMetadata,
}

#[pymethods]
impl PyRowIterMetadata {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>, py: Python<'_>) -> PyResult<Option<Py<PyList>>> {
        match slf.inner.next() {
            None => Ok(None),
            Some(Err(e)) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
            Some(Ok(row)) => {
                let py_row = PyList::empty(py);
                for cell in &row {
                    py_row.append(metadata_to_pydict(py, cell)?)?;
                }
                Ok(Some(py_row.into()))
            }
        }
    }
}

#[pyfunction]
#[pyo3(signature = (path, sheet = None))]
fn stream_rows(path: &str, sheet: Option<&str>) -> PyResult<PyRowIter> {
    let stream = XlsxStream::open(path, sheet)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    let inner = stream
        .rows()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    Ok(PyRowIter { inner })
}

#[pyfunction]
#[pyo3(signature = (path, sheet = None))]
fn stream_rows_with_metadata(path: &str, sheet: Option<&str>) -> PyResult<PyRowIterMetadata> {
    let stream = XlsxStream::open(path, sheet)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    let inner = stream
        .rows_with_metadata()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    Ok(PyRowIterMetadata { inner })
}

// ── Writing ───────────────────────────────────────────────────────────────────

fn pyobject_to_writecell(py: Python<'_>, obj: &PyObject) -> PyResult<WriteCell> {
    let bound = obj.bind(py);

    if bound.is_none() {
        return Ok(WriteCell::Empty);
    }

    // Check PyDateTime before PyDate: datetime is a subclass of date in Python
    if bound.is_instance_of::<PyDateTime>() {
        if let Ok(dt) = bound.downcast::<PyDateTime>() {
            let serial = dates::datetime_to_serial(
                dt.get_year(),
                dt.get_month() as u32,
                dt.get_day() as u32,
                dt.get_hour() as u32,
                dt.get_minute() as u32,
                dt.get_second() as u32,
                dt.get_microsecond(),
            );
            return Ok(WriteCell::DateTime(serial));
        }
    }

    if bound.is_instance_of::<PyDate>() {
        if let Ok(d) = bound.downcast::<PyDate>() {
            let serial =
                dates::date_to_serial(d.get_year(), d.get_month() as u32, d.get_day() as u32);
            return Ok(WriteCell::Date(serial));
        }
    }

    // bool must be checked before f64: bool is a subclass of int in Python
    if let Ok(b) = bound.extract::<bool>() {
        return Ok(WriteCell::Bool(b));
    }
    if let Ok(n) = bound.extract::<f64>() {
        return Ok(WriteCell::Num(n));
    }
    if let Ok(s) = bound.extract::<String>() {
        return Ok(WriteCell::Str(s));
    }
    Ok(WriteCell::Str(bound.str()?.to_string()))
}

#[pyfunction]
fn write(py: Python<'_>, path: &str, rows: PyObject) -> PyResult<()> {
    let mut writer = XlsxWriter::new(path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    for row_obj in rows.bind(py).try_iter()? {
        let row_obj = row_obj?;
        let mut cells: Vec<WriteCell> = Vec::new();
        for cell_obj in row_obj.try_iter()? {
            let cell = cell_obj?.unbind();
            cells.push(pyobject_to_writecell(py, &cell)?);
        }
        writer
            .write_row(&cells, false)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    }
    writer
        .finish()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}

/// Streaming context-manager writer with multi-sheet support.
///
///     with pystreamxl.writer("out.xlsx") as w:
///         w.write_row(["Name", "Age"])
///         w.add_sheet("Sheet2")
///         w.write_row(["City", "Pop"])
#[pyclass]
struct PyXlsxWriter {
    inner: Option<XlsxWriter>,
}

#[pymethods]
impl PyXlsxWriter {
    #[new]
    fn new(path: &str) -> PyResult<Self> {
        let inner = XlsxWriter::new(path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        Ok(Self { inner: Some(inner) })
    }

    #[pyo3(signature = (row, bold = false))]
    fn write_row(&mut self, py: Python<'_>, row: PyObject, bold: bool) -> PyResult<()> {
        let writer = self.inner.as_mut().ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("writer already closed")
        })?;
        let mut cells: Vec<WriteCell> = Vec::new();
        for item in row.bind(py).try_iter()? {
            let cell = item?.unbind();
            cells.push(pyobject_to_writecell(py, &cell)?);
        }
        writer
            .write_row(&cells, bold)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    fn add_sheet(&mut self, name: &str) -> PyResult<()> {
        let writer = self.inner.as_mut().ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("writer already closed")
        })?;
        writer
            .add_sheet(name)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }

    fn close(&mut self) -> PyResult<()> {
        if let Some(w) = self.inner.take() {
            w.finish()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        }
        Ok(())
    }

    fn __enter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __exit__(
        &mut self,
        _exc_type: PyObject,
        _exc_val: PyObject,
        _exc_tb: PyObject,
    ) -> PyResult<bool> {
        self.close()?;
        Ok(false)
    }
}

// ── Module ────────────────────────────────────────────────────────────────────

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(read, m)?)?;
    m.add_function(wrap_pyfunction!(read_with_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(stream_rows, m)?)?;
    m.add_function(wrap_pyfunction!(stream_rows_with_metadata, m)?)?;
    m.add_function(wrap_pyfunction!(write, m)?)?;
    m.add_function(wrap_pyfunction!(sheets, m)?)?;
    m.add_function(wrap_pyfunction!(conditional_formats, m)?)?;
    m.add_class::<PyXlsxWriter>()?;
    m.add_class::<PyRowIter>()?;
    m.add_class::<PyRowIterMetadata>()?;
    Ok(())
}
