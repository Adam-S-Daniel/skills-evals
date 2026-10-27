//! Network settings read from the environment.

use std::fmt;

#[derive(Debug, PartialEq, Eq)]
pub enum ConfigError {
    Missing(&'static str),
    Invalid { key: &'static str, value: String },
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConfigError::Missing(key) => write!(f, "{key} is not set"),
            ConfigError::Invalid { key, value } => write!(f, "{key}={value:?} is not valid"),
        }
    }
}

impl std::error::Error for ConfigError {}
