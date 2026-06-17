use pyo3::prelude::*;
use pyo3::types::{PyDate, PyDateAccess, PyDateTime, PyList, PyTimeAccess};
use streamxl_core::dates;
use streamxl_core::sheet_parser::CellValue;
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
            Ok(PyDate::new_bound(py, year, month as u8, day as u8)?
                .into_any()
                .unbind())
        }
        CellValue::DateTime(n) => {
            let (year, month, day, hour, min, sec, us) = dates::serial_to_datetime(*n);
            Ok(PyDateTime::new_bound(
                py, year, month as u8, day as u8,
                hour as u8, min as u8, sec as u8, us, None,
            )?
            .into_any()
            .unbind())
        }
        CellValue::Empty => Ok(py.None()),
    }
}

#[pyfunction]
#[pyo3(signature = (path, sheet = None))]
fn read(py: Python<'_>, path: &str, sheet: Option<&str>) -> PyResult<Py<PyList>> {
    let stream = XlsxStream::open(path, sheet)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let result = PyList::empty(py);
    for row_result in stream.rows() {
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
fn sheets(path: &str) -> PyResult<Vec<String>> {
    XlsxStream::sheet_names(path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
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
            let serial = dates::date_to_serial(
                d.get_year(),
                d.get_month() as u32,
                d.get_day() as u32,
            );
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
    let mut writer = XlsxWriter::new(path);
    for row_obj in rows.bind(py).try_iter()? {
        let row_obj = row_obj?;
        let mut cells: Vec<WriteCell> = Vec::new();
        for cell_obj in row_obj.try_iter()? {
            let cell = cell_obj?.unbind();
            cells.push(pyobject_to_writecell(py, &cell)?);
        }
        writer.write_row(&cells, false);
    }
    writer
        .finish()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
}

/// Streaming context-manager writer with multi-sheet support.
///
///     with streamxl.writer("out.xlsx") as w:
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
    fn new(path: &str) -> Self {
        Self { inner: Some(XlsxWriter::new(path)) }
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
        writer.write_row(&cells, bold);
        Ok(())
    }

    fn add_sheet(&mut self, name: &str) -> PyResult<()> {
        let writer = self.inner.as_mut().ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("writer already closed")
        })?;
        writer.add_sheet(name);
        Ok(())
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
    m.add_function(wrap_pyfunction!(write, m)?)?;
    m.add_function(wrap_pyfunction!(sheets, m)?)?;
    m.add_class::<PyXlsxWriter>()?;
    Ok(())
}
