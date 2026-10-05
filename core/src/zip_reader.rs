use std::io::{Read, Seek};
use zip::ZipArchive;

// SECURITY: Limits to prevent ZIP bomb (decompression bomb) attacks
// These are conservative limits suitable for enterprise Excel documents
// Most legitimate Excel files are < 50MB. Limits prevent resource exhaustion.
const MAX_ENTRY_SIZE: u64 = 512 * 1024 * 1024; // 512MB per file (reasonable limit for large spreadsheets)
const MAX_TOTAL_SIZE: u64 = 1024 * 1024 * 1024; // 1GB total (prevents consuming all system memory)
const MAX_COMPRESSION_RATIO: f64 = 30.0; // Max 30:1 compression (industry standard ZIP bomb threshold)

pub struct XlsxZip<R: Read + Seek> {
    archive: ZipArchive<R>,
    total_decompressed: u64,
}

impl<R: Read + Seek> XlsxZip<R> {
    pub fn new(reader: R) -> Result<Self, zip::result::ZipError> {
        Ok(Self {
            archive: ZipArchive::new(reader)?,
            total_decompressed: 0,
        })
    }

    /// Pure check against the ZIP-bomb limits (no borrow of `self.archive`,
    /// so it can run while a `ZipFile<'_>` borrowed from `self.archive` is
    /// still alive): returns the new running total on success. Shared by
    /// `read_entry` (which then buffers the body) and
    /// `check_and_register_entry` (which doesn't -- used by callers that
    /// stream the body themselves, see `open_streaming_parser` in stream.rs).
    fn check_entry_limits(
        name: &str,
        compressed_size: u64,
        uncompressed_size: u64,
        current_total: u64,
    ) -> Result<u64, Box<dyn std::error::Error>> {
        if uncompressed_size > MAX_ENTRY_SIZE {
            return Err(format!(
                "ZIP entry '{}' exceeds size limit: {} > {}",
                name, uncompressed_size, MAX_ENTRY_SIZE
            )
            .into());
        }

        if compressed_size > 0 {
            let ratio = uncompressed_size as f64 / compressed_size as f64;
            if ratio > MAX_COMPRESSION_RATIO {
                return Err(format!(
                    "ZIP entry '{}' exceeds compression ratio: {:.1}:1 > {:.1}:1 (potential ZIP bomb)",
                    name, ratio, MAX_COMPRESSION_RATIO
                ).into());
            }
        }

        let new_total = current_total.saturating_add(uncompressed_size);
        if new_total > MAX_TOTAL_SIZE {
            return Err(format!(
                "ZIP total size would exceed limit: {} + {} > {}",
                current_total, uncompressed_size, MAX_TOTAL_SIZE
            )
            .into());
        }
        Ok(new_total)
    }

    pub fn read_entry(&mut self, name: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        let mut entry = self.archive.by_name(name)?;
        let (compressed_size, uncompressed_size) = (entry.compressed_size(), entry.size());
        let new_total = Self::check_entry_limits(
            name,
            compressed_size,
            uncompressed_size,
            self.total_decompressed,
        )?;

        let mut buf = Vec::new();
        entry.read_to_end(&mut buf)?;

        self.total_decompressed = new_total;
        Ok(buf)
    }

    /// Validate a named entry's declared size/compression ratio against the
    /// ZIP-bomb limits (same checks as `read_entry`) without reading or
    /// buffering its body. Used before handing the caller an owned
    /// `ZipArchive` to stream the entry from directly.
    pub fn check_and_register_entry(
        &mut self,
        name: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let entry = self.archive.by_name(name)?;
        let (compressed_size, uncompressed_size) = (entry.compressed_size(), entry.size());
        drop(entry);
        self.total_decompressed = Self::check_entry_limits(
            name,
            compressed_size,
            uncompressed_size,
            self.total_decompressed,
        )?;
        Ok(())
    }

    pub fn has_entry(&mut self, name: &str) -> bool {
        self.archive.by_name(name).is_ok()
    }

    /// Consume this wrapper and hand back the underlying `ZipArchive`, for
    /// callers that need to stream an entry's body directly (`ZipFile<'_>`
    /// borrows `&mut ZipArchive`, so it can't be returned from a method that
    /// also still owns the archive via `XlsxZip`).
    pub fn into_archive(self) -> ZipArchive<R> {
        self.archive
    }
}
