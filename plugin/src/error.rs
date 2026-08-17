use crate::proto::v1::ErrorCode;

#[derive(Debug, thiserror::Error)]
pub enum PluginError {
    #[error("{0}")]
    InvalidArgument(String),
    #[error("{0}")]
    Internal(String),
}

impl PluginError {
    pub fn invalid(message: impl Into<String>) -> Self {
        Self::InvalidArgument(message.into())
    }

    pub fn internal(message: impl Into<String>) -> Self {
        Self::Internal(message.into())
    }

    pub fn code(&self) -> ErrorCode {
        match self {
            Self::InvalidArgument(_) => ErrorCode::InvalidArgument,
            Self::Internal(_) => ErrorCode::Internal,
        }
    }
}

pub type Result<T> = std::result::Result<T, PluginError>;

pub fn check(ok: crate::abi::MpBoolean, message: &str) -> Result<()> {
    if ok == crate::abi::MP_TRUE {
        Ok(())
    } else {
        Err(PluginError::internal(message))
    }
}
