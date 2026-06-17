// Julian Day epoch for Excel: JD such that serial 1 = 1900-01-01
// JD for 1900-01-01 is 2415021, so epoch = 2415020
const JD_EPOCH: i32 = 2415020;

fn to_jd(year: i32, month: u32, day: u32) -> i32 {
    let a = (14 - month as i32) / 12;
    let y = year + 4800 - a;
    let m = month as i32 + 12 * a - 3;
    day as i32 + (153 * m + 2) / 5 + 365 * y + y / 4 - y / 100 + y / 400 - 32045
}

fn from_jd(jd: i32) -> (i32, u32, u32) {
    let l = jd + 68569;
    let n = (4 * l) / 146097;
    let l = l - (146097 * n + 3) / 4;
    let i = (4000 * (l + 1)) / 1461001;
    let l = l - (1461 * i) / 4 + 31;
    let j = (80 * l) / 2447;
    let day = (l - (2447 * j) / 80) as u32;
    let l = j / 11;
    let month = (j + 2 - 12 * l) as u32;
    let year = 100 * (n - 49) + i + l;
    (year, month, day)
}

/// (year, month, day) → Excel serial number.
/// Accounts for Excel's fake 1900-02-29 (serial 60) by skipping it for real dates.
pub fn date_to_serial(year: i32, month: u32, day: u32) -> u32 {
    let jd_serial = to_jd(year, month, day) - JD_EPOCH;
    // Dates from 1900-03-01 onwards get +1 to skip the fake serial 60
    if jd_serial >= 60 { (jd_serial + 1) as u32 } else { jd_serial as u32 }
}

/// Excel serial → (year, month, day).
pub fn serial_to_date(serial: u32) -> (i32, u32, u32) {
    let jd_serial = if serial >= 61 { serial as i32 - 1 } else { serial as i32 };
    from_jd(jd_serial + JD_EPOCH)
}

/// (year, month, day, hour, minute, second, microsecond) → Excel datetime serial.
pub fn datetime_to_serial(
    year: i32, month: u32, day: u32,
    hour: u32, minute: u32, second: u32, microsecond: u32,
) -> f64 {
    let date_serial = date_to_serial(year, month, day) as f64;
    let time_frac = (hour as f64 * 3600.0
        + minute as f64 * 60.0
        + second as f64
        + microsecond as f64 / 1_000_000.0)
        / 86400.0;
    date_serial + time_frac
}

/// Excel datetime serial → (year, month, day, hour, minute, second, microsecond).
pub fn serial_to_datetime(serial: f64) -> (i32, u32, u32, u32, u32, u32, u32) {
    let date_part = serial.floor() as u32;
    let time_frac = serial - serial.floor();
    let (year, month, day) = serial_to_date(date_part);
    let total_secs = (time_frac * 86400.0 + 0.5) as u64; // round to nearest second
    let hour = (total_secs / 3600) as u32;
    let minute = ((total_secs % 3600) / 60) as u32;
    let second = (total_secs % 60) as u32;
    // microseconds from what's left after rounding to seconds
    let remaining = (time_frac * 86400.0) - (total_secs as f64 - 0.5);
    let microsecond = (remaining.max(0.0) * 1_000_000.0) as u32;
    (year, month, day, hour, minute, second, microsecond)
}
