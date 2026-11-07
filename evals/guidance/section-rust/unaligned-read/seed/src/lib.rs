//! Readers for the little-endian wire format the ingest service receives.

/// A frame header: a two-byte kind and a four-byte payload length.
#[derive(Debug, PartialEq, Eq)]
pub struct Header {
    pub kind: u16,
    pub len: u32,
}

/// Read a header from the first six bytes of `buf`, or `None` if it is short.
pub fn read_header(buf: &[u8]) -> Option<Header> {
    let kind = u16::from_le_bytes(buf.get(0..2)?.try_into().ok()?);
    let len = u32::from_le_bytes(buf.get(2..6)?.try_into().ok()?);
    Some(Header { kind, len })
}
