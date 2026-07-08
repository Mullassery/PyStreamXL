use std::io::{Read, Seek};
use zip::ZipArchive;

// SECURITY: Limits to prevent ZIP bomb (decompression bomb) attacks
const MAX_ENTRY_SIZE: u64 = 2 * 1024 * 1024 * 1024; // 2GB per file
const MAX_TOTAL_SIZE: u64 = 10 * 1024 * 1024 * 1024; // 10GB total
const MAX_COMPRESSION_RATIO: f64 = 100.0; // Max 100:1 compression

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

    pub fn read_entry(&mut self, name: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        let mut entry = self.archive.by_name(name)?;

        let compressed_size = entry.compressed_size();
        let uncompressed_size = entry.size();

        // Check individual file size limits
        if uncompressed_size > MAX_ENTRY_SIZE {
            return Err(format!(
                "ZIP entry '{}' exceeds size limit: {} > {}",
                name, uncompressed_size, MAX_ENTRY_SIZE
            )
            .into());
        }

        // Check compression ratio (ZIP bomb detection)
        if compressed_size > 0 {
            let ratio = uncompressed_size as f64 / compressed_size as f64;
            if ratio > MAX_COMPRESSION_RATIO {
                return Err(format!(
                    "ZIP entry '{}' exceeds compression ratio: {:.1}:1 > {:.1}:1 (potential ZIP bomb)",
                    name, ratio, MAX_COMPRESSION_RATIO
                ).into());
            }
        }

        // Check total uncompressed size
        let new_total = self.total_decompressed.saturating_add(uncompressed_size);
        if new_total > MAX_TOTAL_SIZE {
            return Err(format!(
                "ZIP total size would exceed limit: {} + {} > {}",
                self.total_decompressed, uncompressed_size, MAX_TOTAL_SIZE
            )
            .into());
        }

        let mut buf = Vec::new();
        entry.read_to_end(&mut buf)?;

        self.total_decompressed = new_total;
        Ok(buf)
    }

    pub fn has_entry(&mut self, name: &str) -> bool {
        self.archive.by_name(name).is_ok()
    }
}
